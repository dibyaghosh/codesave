import inspect
import tempfile
import sys
import shutil
import datetime
import glob
import importlib
from pathlib import Path
import zipfile
from typing import Union, List, Callable
import json

_is_pycache = lambda fname: fname.endswith(".pyc")


def create_zip(
    files_and_folders: Union[List, str],
    output_zipname: str,
    library_names=None,
    ignore_file_patterns: List[Callable[[str], bool]] = (_is_pycache,),
    verbose: bool = True,
):
    """Creates a zipfile of your codebase, for reference and to investigate!

    The resulting zip file can be used as a backup of your codebase (just unzip it and you're good to go!)
    but it can also be used more directly:

    export PYTHONPATH=$PYTHONPATH:$(pwd)/codebase.zip
    # Now you can import libraries from codebase.zip

    Args:
        files_and_folders: A list of files and folders to include in the zip file.
            If a string is passed, it will be treated as a single file or folder.
        output_zipname: The name of the zip file to create
        library_names: A list of libraries that can be imported.
            If None, will be inferred from the files_and_folders
        ignore_file_patterns: A list of filtering functions. Each element should
          be a function that takes a filename and returns True if it should be ignored.
          By default, we ignore pycache folders.
    """

    verbose_print = print if verbose else lambda *a, **k: None

    files_and_folders = (
        [files_and_folders] if isinstance(files_and_folders, str) else files_and_folders
    )
    files_and_folders = [
        Path(og_dir).expanduser().resolve() for og_dir in files_and_folders
    ]

    with tempfile.TemporaryDirectory() as main_dir:
        main_dir = Path(main_dir)

        for og_dir in files_and_folders:
            target_dir = main_dir / og_dir.name
            verbose_print("Copying code from {} to {}".format(og_dir, target_dir))
            if og_dir.is_file():
                shutil.copy(og_dir, target_dir)
            else:
                shutil.copytree(og_dir, target_dir, dirs_exist_ok=True)

        verbose_print("Creating zip file at {}".format(output_zipname))
        with zipfile.ZipFile(output_zipname, "w") as zip:
            files_to_add = glob.glob(str(main_dir / "**"), recursive=True)
            files_to_add = [
                f
                for f in files_to_add
                if not any([pattern(f) for pattern in ignore_file_patterns])
            ]
            for file in files_to_add:
                new_name = Path(file).relative_to(main_dir)
                zip.write(file, arcname=new_name)

            if library_names is None:
                library_names = _get_library_names(zip.namelist())
            zip.writestr("library_names.json", json.dumps(library_names))

    print("Saved codebase to ", output_zipname)


def create_unique_zip(
    input_zipname: str,
    output_zipname: str,
    prefix: str = None,
    library_names: bool = None,
    verbose: bool = True,
    save_non_code: bool = True,
    add_init: bool = True,
):
    """
    Turns a zip from `create_zip` into a zip that can be *jointly loaded* with other codebases using ZipCodebase.

    There exist multiple use-cases:
        1. We want to load multiple versions of a codebase at once
        2. We want to load multiple codebases with conflicting versions of the same dependency

    Args:
        input_zipname: The zip file to convert
        output_zipname: The path to save the zip file to
        prefix: A prefix that will be added to all imports. If None, defaults to `codebase_<timestamp>`
            This is what allows us to load multiple versions of the same codebase.

    """
    verbose_print = print if verbose else lambda *a, **k: None
    prefix = prefix or "codebase_{:}".format(
        datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    )
    with zipfile.ZipFile(input_zipname, "r") as zip:
        with zipfile.ZipFile(output_zipname, "w") as new_zip:
            namelist = zip.namelist()
            if library_names is None:
                if "library_names.json" in namelist:
                    library_names = json.loads(
                        zip.read("library_names.json").decode("utf-8")
                    )
                else:
                    library_names = _get_library_names(namelist)
            verbose_print("Found libraries: ", library_names)
            verbose_print('Adding prefix "{}"'.format(prefix))
            for info in zip.infolist():
                old_filename = info.filename
                info.filename = prefix + "/" + info.filename

                if not info.filename.endswith(".py") and save_non_code:
                    new_zip.writestr(info, zip.read(old_filename))
                else:
                    s = zip.read(old_filename).decode("utf-8")
                    s = _fix_all_imports(
                        s,
                        library_names,
                        new_pattern=lambda library: f"{prefix}.{library}",
                        old_pattern=lambda library: f"{library}",
                        verbose=True,
                    )
                    new_zip.writestr(info, s)

            newzip_files = new_zip.namelist()
            necessary_inits = set()
            for file in newzip_files:
                if file.endswith(
                    ".py"
                ):  # add __init__.py to all folders leading up to this file
                    all_parts = file.split("/")
                    for i in range(1, len(all_parts) - 1):
                        necessary_inits.add("/".join(all_parts[:i] + ["__init__.py"]))
            for init in necessary_inits:
                if init not in newzip_files:
                    new_zip.writestr(init, "")
                    verbose_print("Adding  ", init)
    print("Saved unique codebase to ", output_zipname)


class ZipCodebase:
    """
    A codebase that you can use with the output of `create_unique_zip`.

    Once a ZipCodebase is created, you can import from it in a few ways:

    ```
    create_zip('codesave.py', 'test.zip')
    cs = ZipCodebase('test.zip')

    # Equivalent to `import codesave`
    cs._import('codesave')

    # Equivalent to `from codesave import create_zip`
    cs._from_import('codesave', 'create_zip')

    # Equivalent to `from codesave import create_zip, ZipCodebase`
    cs._from_import('codesave', ['create_zip', 'ZipCodebase'])

    # Equivalent to `importlib.import_module('codesave')`
    cs.import_module('codesave')

    # Equivalent to `import codesave`
    import codebase_20230927210132.codesave as codesave # see cs.library_name for the actual prefix

    """

    def __init__(self, zip_name: str, verbose: bool = False, make_unique: bool = True):
        if make_unique:
            tmp_name = tempfile.mktemp(suffix=".zip")
            print("Making unique copy of ", zip_name, " at ", tmp_name)
            create_unique_zip(zip_name, tmp_name, verbose=verbose)
            zip_name = tmp_name
        else:
            print("Are you sure you already ran `create_unique_zip`?")

        with zipfile.ZipFile(zip_name, "r") as zip:
            all_files = zip.namelist()
            self._library_name = all_files[0].split("/")[0]

        sys.path.insert(0, zip_name)
        self.valid_libraries = list(
            set(
                [
                    f.replace(".py", "").split("/")[1]
                    for f in all_files
                    if ".py" in f and "__init__" not in f.split("/")[1]
                ]
            )
        )

        print("Found libraries in codebase: ", self.valid_libraries)

        if verbose:
            print("You can now import either as: ")
            print("> import {}.{}".format(self.library_name, self.valid_libraries[0]))
            print("or as:")
            print('> codebase._import("{0}")'.format(self.valid_libraries[0]))

    @property
    def library_name(self):
        return self._library_name

    def _import(self, name, _as=None):
        """ """
        print("Trying to import ", f"{self.library_name}.{name}")
        lib = importlib.import_module(f"{self.library_name}.{name}")
        if _as is None:
            _as = name
            if (
                "." in name
            ):  # Dealing with the fact that import a.b should return a, not b
                _as = name.split(".")[0]
                lib = importlib.import_module(f"{self.library_name}.{_as}")
        calling_locals = inspect.stack()[1].frame.f_locals
        calling_locals[_as] = lib

    def import_module(self, name):
        """
        Replicates the behavior of `importlib.import_module`.
        """

        print("Trying to import ", f"{self.library_name}.{name}")
        return importlib.import_module(f"{self.library_name}.{name}")

    def _from_import(self, name, things_to_import):
        module = self.import_module(name)
        if isinstance(things_to_import, str):
            things_to_import = [things_to_import]
        calling_locals = inspect.stack()[1].frame.f_locals
        for thing in things_to_import:
            try:
                calling_locals[thing] = getattr(module, thing)
            except:
                calling_locals[thing] = self.import_module(name + "." + thing)


def _fix_all_imports(
    original_text,
    libraries,
    new_pattern,
    old_pattern=lambda library: f"{library}",
    verbose=True,
):
    all_changes = []
    for library in libraries:
        op = old_pattern(library)
        np = new_pattern(library)
        all_changes.append((f"import {op} ", f"import {np} "))
        all_changes.append((f"import {op}.", f"import {np}."))
        all_changes.append((f"from {op}.", f"from {np}."))

    new_s = original_text
    for old_string, new_string in all_changes:
        new_s = new_s.replace(old_string, new_string)
    return new_s
    # if verbose:
    #     for l1, l2 in zip(s.split("\n"), new_s.split("\n")):
    #         if l1 != l2:
    #             print(f"< {l1} \n> {l2}")

    if not dry:
        with open(file_path, "w") as f:
            f.write(new_s)


def _get_library_names(all_fnames, index=0):
    """
    Given a list of file names (relative to the current path),
    returns a list of libraries that can be imported.

    These are either python files in the top directory, or directories with python files in them.

    """
    return list(
        set([f.split("/")[index].replace(".py", "") for f in all_fnames if ".py" in f])
    )
