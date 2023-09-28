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

```python
from codesave import ZipCodebase
codebase1 = ZipCodebase('codebase.zip')
codebase2 = ZipCodebase('codebase_v2.zip')
codebase1._from('src', 'model' _as='model_v1')
# equivalent to (from src import model as model_v1) from codebase.zip
codebase2._from('src', 'model' _as='model_v2')
# equivalent to (from src import model as model_v2) from codebase_v2.zip
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
