from codesave import (
    create_zip,
    ZipCodebase,
    checkpoint_codebase,
    create_unique_zip,
    checkpoint_codebase_for_wandb,
)

main_folder = "~/nfs2/playground/advantage_learning"
extra_pythonpath = ("~/nfs2/playground/jaxrl_m",)
extra_libraries = tuple()

checkpoint_codebase(
    main_folder=main_folder,
    extra_pythonpath=extra_pythonpath,
    extra_libraries=extra_libraries,
    output_zipname="test.zip",
    verbose=False,
)
# create_unique_zip("test.zip", "test2.zip")
cs = ZipCodebase("test.zip", verbose=False, make_unique=True)

# Test wandb
# import wandb

# wandb.init(project="test")
# checkpoint_codebase_for_wandb(
#     main_folder=main_folder,
#     extra_pythonpath=extra_pythonpath,
#     extra_libraries=extra_libraries,
#     verbose=True,
# )
