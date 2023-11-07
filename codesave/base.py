import inspect
import tempfile
import sys
import shutil
import datetime
import importlib
from pathlib import Path
import zipfile
from typing import Union, List, Callable
import json
import fnmatch
import pkg_resources

DEFAULT_MAIN = """
import sys
help_text = '''
    This is a codebase saved with codesave. You can run files within it like:
        python codebase.zip module_name:fn_name ...
        python codebase.zip file.py ...
'''
print(sys.argv)
assert len(sys.argv) >= 2, help_text
module_name = sys.argv.pop(1)
if ":" in module_name:
    import importlib
    module_name, fn_name = module_name.split(":")
    module = importlib.import_module(module_name)
    getattr(module, fn_name)()
else:
    import runpy
    module_name = module_name.replace(".py", "").replace("/", ".")
    print("Running ", module_name)
    runpy.run_module(module_name)
"""

def create_zip(
    files_and_folders: Union[List[Path], Path, str],
    output_zipname: str,
    library_names=None,
    ignore: Callable = None,
    verbose: bool = True,
):
    """Creates a zipfile of your codebase, for reference and to investigate!

    The resulting zip file can be used as a backup of your codebase (just unzip it and you're good to go!)
    but it can also be used more directly:

        PYTHONPATH=codebase.zip python
        >>> import src.models # You can import from the codebase!
    
    or
        python codebase.zip train.py # You can run files within the codebase!

    Args:
        files_and_folders: A list of files and folders to include in the zip file.
            If a string is passed, it will be treated as a single file or folder.
        output_zipname: The name of the zip file to create
        library_names: A list of libraries that can be imported.
            If None, will be inferred from the files_and_folders
        ignore: A filtering function that will be passed to `shutil.copytree` to ignore files.
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
            if ignore is not None:
                if ignore(str(og_dir.parent), [og_dir.name]):
                    verbose_print("Ignoring ", og_dir)
                    continue

            if og_dir.is_file():
                shutil.copy(og_dir, target_dir)
            else:
                shutil.copytree(og_dir, target_dir, dirs_exist_ok=True, ignore=ignore)

        verbose_print("Creating zip file at {}".format(output_zipname))
        if library_names is None:
            all_pyfiles = map(str, main_dir.glob("**/*.py"))
            library_names = _get_library_names(all_pyfiles, index=0)
        with open(main_dir / "library_names.json", "w") as f:
            json.dump(library_names, f)
        with open(main_dir / "packages.txt", "w") as f:
            for lib in pkg_resources.working_set:
                f.write(repr(lib) + "\n")
        if not (main_dir / "__main__.py").exists():
            with open(main_dir / "__main__.py", "w") as f:
                f.write(DEFAULT_MAIN)
            
        shutil.make_archive(
            str(output_zipname),
            "zip",
            root_dir=main_dir,
            verbose=verbose,
        )
        shutil.move(str(output_zipname) + ".zip", output_zipname)        
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
                    )
                    new_zip.writestr(info, s)

            if add_init:
                newzip_files = new_zip.namelist()
                necessary_inits = set()
                for file in newzip_files:
                    if file.endswith(
                        ".py"
                    ):  # add __init__.py to all folders leading up to this file
                        all_parts = file.split("/")
                        for i in range(1, len(all_parts) - 1):
                            necessary_inits.add(
                                "/".join(all_parts[:i] + ["__init__.py"])
                            )
                for init in necessary_inits:
                    if init not in newzip_files:
                        new_zip.writestr(init, "")
                        verbose_print("Adding  ", init)

    print("Saved unique codebase to ", output_zipname)

def change_launcher(zip_file: str, external_path: str = None,  internal_path: str = None, module_name: str = None):
    """Makes the zip file runnable by adding a launcher.py file to it."""
    assert sum([x is not  None for x in [external_path, module_name, internal_path]]) == 1, "Exactly one of external_path, module_name, internal_path must be provided."

    tmp_name = None
    with zipfile.ZipFile(zip_file, "r") as input_zip:    
        if '__main__.py' in input_zip.namelist():
            tmp_name = tempfile.mktemp(suffix=".zip")
            with zipfile.ZipFile(tmp_name, "w") as output_zip:
                for info in input_zip.infolist():
                    if info.filename != '__main__.py':
                        output_zip.writestr(info, input_zip.read(info.filename))

    if tmp_name is not None:
        shutil.move(tmp_name, zip_file)


    with zipfile.ZipFile(zip_file, "a") as zf:
        if external_path is not None:
            launcher_path = Path(external_path).resolve()
            zf.write(launcher_path, arcname="__main__.py")
        elif internal_path is not None:
            bytes = zf.read(internal_path)
            zf.writestr("__main__.py", bytes)
        elif module_name is not None:
            launcher = """import runpy; runpy.run_module("{}")""".format(module_name)
            zf.writestr("__main__.py", launcher)


class Codebase:
    _ran_already = False
    """
    A codebase that you can use with the output of `create_zip`.
    Be careful about making multiple Codebases in a single script,
    as caching may cause you to ignore the new codebase. Use UniqueCodebase
    to handle these use-cases.

    Usage:
    > with Codebase('codebase.zip'):
        import src.models
    > # Imports won't work after this

    or
    > cs = Codebase('codebase.zip')
    > import src.models
    > cs.close() # Imports won't work after this

    """

    def __init__(self, zip_name: str, verbose: bool = False):
        with zipfile.ZipFile(zip_name, "r") as zip:
            all_files = zip.namelist()

        self.zip_name = zip_name
        self.valid_libraries = list(
            set(
                [
                    f.replace(".py", "").split("/")[0]
                    for f in all_files
                    if ".py" in f and "__init__" not in f.split("/")[1]
                ]
            )
        )

        if verbose:
            print("Found libraries in codebase: ", self.valid_libraries)
        sys.path.insert(0, self.zip_name)
        if Codebase._ran_already:
            print(
                "Warning: "
                "You have already made a Codebase."
                "Creating more codebases may cause issues."
                "Use UniqueCodebase to handle these use-cases."
            )
        Codebase._ran_already = True

    def close(self):
        """
        Removes the codebase from the path. But existing imported modules will still work.
        """
        sys.path.remove(self.zip_name)
        importlib.invalidate_caches()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class UniqueCodebase:
    """
    A codebase so that you can load multiple versions of the same codebase,
    or multiple codebases at the same time.

    Once a UniqueCodebase is created, you can import from it in a few ways:

    ```
    create_zip('codesave.py', 'test.zip')
    cs = UniqueCodebase('test.zip')

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

        self.zip_name = zip_name
        sys.path.insert(0, zip_name)
        importlib.invalidate_caches()

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

    def import_module(self, name):
        """
        Replicates the behavior of `importlib.import_module`.
        """

        return importlib.import_module(f"{self.library_name}.{name}")

    def import_(self, name, as_=None):
        """ """
        print("Importing ", f"{self.library_name}.{name}")
        lib = importlib.import_module(f"{self.library_name}.{name}")
        if as_ is None:
            as_ = name
            if (
                "." in name
            ):  # Dealing with the fact that import a.b should return a, not b
                as_ = name.split(".")[0]
                lib = importlib.import_module(f"{self.library_name}.{as_}")
        calling_locals = inspect.stack()[1].frame.f_locals
        calling_locals[as_] = lib

    def from_import(self, name, things_to_import, as_=None):
        module = self.import_module(name)
        if isinstance(things_to_import, str):
            things_to_import = [things_to_import]

        calling_locals = inspect.stack()[1].frame.f_locals
        if as_ is not None:
            assert len(things_to_import) == 1
            as_ = {as_: things_to_import[0]}
        else:
            as_ = {t: t for t in things_to_import}

        ret = []
        for ass, thing in as_.items():
            try:
                calling_locals[ass] = getattr(module, thing)
            except:
                calling_locals[ass] = self.import_module(name + "." + thing)
            ret.append(calling_locals[ass])
        if len(ret) == 1:
            return ret[0]
        return ret

    def close(self):
        sys.path.remove(self.zip_name)
        importlib.invalidate_caches()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def _fix_all_imports(
    original_text,
    libraries,
    new_pattern,
    old_pattern=lambda library: f"{library}",
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


def _get_library_names(all_fnames, index=0):
    """
    Given a list of file names (relative to the current path),
    returns a list of libraries that can be imported.

    These are either python files in the top directory, or directories with python files in them.

    """
    return list(
        set([f.split("/")[index].replace(".py", "") for f in all_fnames if ".py" in f])
    )


class shutil_filters:
    # Factory functions for creating filters for shutil.copytree

    @staticmethod
    def chain(*fns):
        def chained_fn(path, names):
            excluded = set()
            for fn in fns:
                excluded.update(fn(path, names))
            return list(excluded)

        return chained_fn

    @staticmethod
    def ignore_larger_than(size):
        if isinstance(size, str):
            try:
                size, modifier = int(size[:-1]), size[-1].lower()
                modifier = {"k": 1e3, "m": 1e6, "g": 1e9}[modifier]
                size *= modifier
            except:
                raise ValueError(
                    "Could not parse size argument. Expected something like '1k', '10m', '1g'"
                )

        def fn(path, names):
            excluded_names = []
            for name in names:
                name_path = Path(path) / name
                if name_path.is_file() and name_path.stat().st_size > size:
                    excluded_names.append(name)
            return excluded_names

        return fn

    @staticmethod
    def ignore_patterns(*glob_patterns):
        return shutil.ignore_patterns(*glob_patterns)

    @staticmethod
    def include_only_patterns(*glob_patterns):
        def fn(path, names):
            excluded_names = []
            for name in names:
                name_path = Path(path) / name
                if name_path.is_file():
                    if not any(
                        [
                            fnmatch.fnmatch(name_path, glob_pattern)
                            for glob_pattern in glob_patterns
                        ]
                    ):
                        excluded_names.append(name)
            return excluded_names

        return fn
