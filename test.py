import argparse

from codesave import (
    Codebase,
    UniqueCodebase,
    create_unique_zip,
    checkpoint,
    checkpoint_to_wandb,
    download_from_wandb,
)

main_folder = "~/nfs2/playground/advantage_learning"
extra_pythonpath = tuple()
extra_libraries = ("~/nfs2/playground/jaxrl_m/jaxrl_m",)


def test_creation():
    checkpoint(
        main_folder=main_folder,
        extra_pythonpath=extra_pythonpath,
        extra_libraries=extra_libraries,
        output_zipname="test.zip",
        verbose=False,
    )
    create_unique_zip("test.zip", "test2.zip")


# Test wandb
def test_wandb():
    import wandb
    import tempfile

    wandb.init(project="test")
    checkpoint_to_wandb(
        main_folder=main_folder,
        extra_pythonpath=extra_pythonpath,
        extra_libraries=extra_libraries,
        verbose=True,
    )
    wandb_path = wandb.run.path
    wandb.run.finish()
    out = download_from_wandb(wandb_path, output_zipname=tempfile.mktemp(suffix=".zip"))
    print(f"Download from wandb:{wandb_path} to {out}")
    with UniqueCodebase(out) as cb:
        PRNGKey = cb.from_import("jaxrl_m.typing", "PRNGKey")
    print(PRNGKey)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb", action="store_true")
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--test", type=bool, default=True)
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()
    if args.all:
        args.wandb = True
        args.create = True
        args.test = True
    if args.wandb:
        test_wandb()
    if args.create:
        test_creation()
    if args.test:
        with Codebase("test.zip"):
            from jaxrl_m.typing import PRNGKey
        print(PRNGKey)

        with UniqueCodebase("test.zip") as cs:
            cs.from_import("jaxrl_m.typing", "PRNGKey")
        print(PRNGKey)
