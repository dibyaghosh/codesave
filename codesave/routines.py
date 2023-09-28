from .base import create_zip
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


def checkpoint_codebase(
    main_folder,
    extra_pythonpath=tuple(),
    extra_libraries=tuple(),
    output_zipname=None,
    verbose=True,
):
    assert output_zipname is not None, "output_zipname must be specified"

    verbose_print = print if verbose else lambda *args, **kwargs: None
    all_libs = {}
    for path in extra_pythonpath:
        all_libs.update(_get_python_libraries(Path(path)))
    all_libs.update(_get_python_libraries(Path(main_folder)))
    assert len(extra_libraries) == 0, "Not implemented yet"

    all_files = list(all_libs.values())
    all_files.extend(
        glob.glob(str(Path(main_folder).expanduser().resolve() / "*"), recursive=True)
    )

    verbose_print("All files: ", all_files)
    verbose_print("All libs: ", all_libs.keys())
    create_zip(
        all_files,
        output_zipname=output_zipname,
        library_names=list(all_libs.keys()),
        verbose=verbose,
    )


def checkpoint_codebase_for_wandb(
    main_folder,
    extra_pythonpath=tuple(),
    extra_libraries=tuple(),
    output_directory=None,
    verbose=True,
):
    import wandb

    output_directory = output_directory or wandb.run.dir
    output_directory = Path(output_directory).expanduser().resolve()

    output_zipname = output_directory / "codebase.zip"
    checkpoint_codebase(
        main_folder=main_folder,
        extra_pythonpath=extra_pythonpath,
        extra_libraries=extra_libraries,
        output_zipname=output_zipname,
        verbose=verbose,
    )

    with open(output_directory / "packages.txt", "w") as f:
        for lib in pkg_resources.working_set:
            f.write(repr(lib) + "\n")

    wandb.save(str(output_zipname), policy="now")
    wandb.save(str(output_directory / "packages.txt"), policy="now")


def load_codebase_from_wandb(
    runname=None,
    wandb_filename="codebase.zip",
    output_zipname=None,
):
    """
    Downloads the codebase.zip file from the runname run, and saves it to output_zipname.

    Returns the output_zipname.
    """

    import wandb

    api = wandb.Api()
    run = api.run(runname)
    file = run.file(wandb_filename)
    output_zipname = output_zipname or tempfile.mktemp(suffix=".zip")
    with tempfile.TemporaryDirectory() as tmpdirname:
        file.download(tmpdirname)
        shutil.copy2(Path(tmpdirname) / wandb_filename, output_zipname)
    return output_zipname
