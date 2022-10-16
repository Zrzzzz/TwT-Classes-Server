# Usage

```
conda env create -n server python=3.8
conda activate server
pip install -r requirements.txt
gunicorn -c gunicorn.conf.py app:app
```