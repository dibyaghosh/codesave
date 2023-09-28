from .base import create_zip, shutil_filters
import glob
from pathlib import Path
import tempfile
import pkg_resources
import shutil


def _get_python_libraries(pythonpath: Path):
    pythonpath = pythonpath.expanduser().resolve()
    assert pythonpath.is_dir()
    libs = {}
    for path in pythonpath.iterdir():
        if path.suffix == ".py":
            libs[path.stem] = path
        elif path.is_dir():
            if len(glob.glob(str(path / "**/*.py"), recursive=True)) > 0:
                libs[path.name] = path
    return libs


def checkpoint(
    main_folder,
    output_zipname=None,
    extra_libraries=tuple(),
    extra_pythonpath=tuple(),
    ignore_patterns=tuple(),
    py_only=False,
    ignore_larger_than=None,  # e.g. "1M"
    verbose=True,
):
    """Saves a zip file containing all the files in main_folder (and potentially some extra libraries).

    Arguments:
        main_folder: Everything in this folder will be saved to the zip file. This directory will be
            what gets added to the python path when the codebase is loaded again.
        extra_libraries: Extra libraries (either files / folders) to add to the zip file. These libraries will effectively
          be placed *within* the main_folder when the codebase is loaded again, so make sure you choose the right folder level.
        extra_pythonpath: Every folder in this list will be searched for python libraries to add to the codebase.
            Recommended to not use this, as searching for libraries in a large folder can be *very* slow.
        ignore_patterns: Files matching any of these glob patterns will be ignored.
        py_only: If True, only .py files will be saved.
        ignore_larger_than: Files larger than this will be ignored. Useful to avoid saving large files like datasets or checkpoints.
        output_zipname: Name of the zip file to save to. Defaults to "codebase.zip"


    To avoid some confusion about `extra_libraries` vs. `extra_pythonpath`: if the external library looks like this:

        > my_library
            > my_library
                > __init__.py
                > my_code.py
            > setup.py
            > README.md

    Then, when using `extra_libraries`, you should specify the path to the *child* folder, i.e. `my_library/my_library`.
    When using `extra_pythonpath`, you should specify the path to the *parent* folder, i.e. `my_library`.

    """
    assert output_zipname is not None, "output_zipname must be specified"

    verbose_print = print if verbose else lambda *args, **kwargs: None
    all_libs = {}
    for path in extra_pythonpath:
        all_libs.update(_get_python_libraries(Path(path)))
    all_libs.update(_get_python_libraries(Path(main_folder)))

    for path in extra_libraries:
        path = Path(path).expanduser().resolve()
        all_libs[path.stem] = path

    all_files = list(all_libs.values())
    all_files.extend(
        glob.glob(str(Path(main_folder).expanduser().resolve() / "*"), recursive=True)
    )

    verbose_print("All files: ", all_files)
    verbose_print("All libs: ", all_libs.keys())

    ignore = []
    if len(ignore_patterns) > 0:
        verbose_print("Ignoring patterns: ", ignore_patterns)
        ignore.append(shutil_filters.ignore_patterns(ignore_patterns))
    if py_only:
        verbose_print("Ignoring all py files")
        ignore.append(shutil_filters.include_only_patterns("*.py"))
    if ignore_larger_than is not None:
        verbose_print("Ignoring files larger than: ", ignore_larger_than)
        ignore.append(shutil_filters.ignore_larger_than(ignore_larger_than))

    if len(ignore) > 0:
        ignore = shutil_filters.chain(*ignore)
    else:
        ignore = None

    create_zip(
        all_files,
        output_zipname=output_zipname,
        library_names=list(all_libs.keys()),
        ignore=ignore,
        verbose=verbose,
    )


def checkpoint_to_wandb(
    main_folder,
    output_directory=None,
    extra_libraries=tuple(),
    extra_pythonpath=tuple(),
    ignore_patterns=tuple(),
    py_only=False,
    ignore_larger_than="100K",  # Be conservative by default for wandb, since the file needs to be uploaded
    verbose=True,
    codebase_zipname="codebase.zip",
):
    """See checkpoint_codebase, but also saves the zip file to wandb.

    New arguments:
    - output_directory: codebase will be saved to `output_directory / codebase_zipname`.
        Defaults to wandb.run.dir
    - codebase_zipname: name of the zip file to save to. Defaults to "codebase.zip"
        Note: this will be the name of the file on wandb too. You will need it to download it in the future.
    """
    import wandb

    output_directory = output_directory or wandb.run.dir
    output_directory = Path(output_directory).expanduser().resolve()

    output_zipname = output_directory / codebase_zipname
    checkpoint(
        main_folder=main_folder,
        extra_pythonpath=extra_pythonpath,
        extra_libraries=extra_libraries,
        output_zipname=output_zipname,
        ignore_patterns=ignore_patterns,
        py_only=py_only,
        ignore_larger_than=ignore_larger_than,
        verbose=verbose,
    )

    with open(output_directory / "packages.txt", "w") as f:
        for lib in pkg_resources.working_set:
            f.write(repr(lib) + "\n")

    wandb.save(str(output_zipname), policy="now")
    wandb.save(str(output_directory / "packages.txt"), policy="now")


def download_from_wandb(
    wandb_path=None,
    wandb_filename="codebase.zip",
    output_zipname=None,
    api=None,
):
    """
    Downloads the codebase.zip file from the runname run, and saves it to output_zipname.

    Returns the output_zipname.
    """
    if api is None:
        import wandb

        api = wandb.Api()
    run = api.run(wandb_path)
    file = run.file(wandb_filename)
    output_zipname = output_zipname or tempfile.mktemp(suffix=".zip")
    with tempfile.TemporaryDirectory() as tmpdirname:
        file.download(tmpdirname)
        shutil.copy2(Path(tmpdirname) / wandb_filename, output_zipname)
    return output_zipname
