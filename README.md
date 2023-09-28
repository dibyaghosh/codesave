# Codesave


### TL;DR

```python
### When training
from codesave import checkpoint_to_wandb
wandb.init(...)
checkpoint_to_wandb(codebase_dirname)

### Time to recover
from codesave import Codebase, download_from_wandb
zipname = download_from_wandb(wandb_run_path)
with Codebase(zipname):
    from src import model
    model.whatever_you_want
```

### Installation:

```
pip install code-save
```

```
pip install git+https://github.com/dibyaghosh/codesave.git
```

### Basic Usage

The easiest way to use codesave is using `checkpoint` or `checkpoint_to_wandb`, which will take all the files in the directory and create a zip file.

For example, suppose we have some repository with the following structure:

    codebase/
        src/
            model.py
            utils.py
        train.py
        eval.py

```
from codesave import checkpoint, checkpoint_to_wandb
checkpoint('codebase/', output_zipname='codebase.zip')
checkpoint_to_wandb('codebase/') # Stores it in the current wandb run (on the cloud)
```

This creates a zipfile that we can use anywhere else  (even if we don't have codesave installed):

```
import sys
sys.path.append('codebase.zip')
import src.model # This will load the library directly from the zip file
```

# Loading a Codebase

### Using `sys.path`

The easiest way, doesn't require `codesave` to be installed

```python
import sys
sys.path.append('codebase.zip') # Or PYTHONPATH=codebase.zip:$PYTHONPATH
import src.model # This will load the library directly from the zip file
```

### Using `Codebase`

The second easiest way, but **cannot be run multiple times in the same process** (because old modules are not unloaded)

```python
from codesave import Codebase
with Codebase('codebase.zip'):
    from src import model
    model.whatever_you_want
```

### Using `UniqueCodebase` (general, recommended)

Using UniqueCodebase, we can load as many versions of a codebase as we want, and they can interact with each other.

The import notation is a little less clean, but it's necessary to avoid conflicts.

```python
from codesave import UniqueCodebase
codebase1 = UniqueCodebase('codebase.zip')
codebase2 = UniqueCodebase('codebase_v2.zip')
model_v1 = codebase1.import_module('src.model') # equivalent to (from src import model as model_v1) from codebase.zip
model_v2 = codebase2.import_module('src.model') # equivalent to (from src import model as model_v2) from codebase_v2.zip
```

There are some syntactic sugar options (these do some magic juju to automatically assign the module to a variable)

```
codebase1.import_('src.model') # equivalent to `import src.model`
codebase1.import_('src.model', as_='model_v1') # equivalent to `import src.model as model_v1`
codebase1.from_import('src', ('model', 'utils')) # equivalent to `from src import model, utils`
codebase1.from_import('src', 'model', as_='model_v1') # equivalent to `from src import model as model_v1`

```


### Just Unzip It

You can always unzip the zip file, and treat it as a normal directory.

## Integration w/ wandb

When training,
```
from codesave import checkpoint_codebase_for_wandb
wandb.init(...)
checkpoint_codebase_for_wandb('codebase/')
```

Now at any point,
```
from codesave import load_codebase_from_wandb
load_codebase_from_wandb(wandb_run_name, output_zipname='codesave.zip')
# Now we can add to sys.path or ZipCodebase as before
```
