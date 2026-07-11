import os
from starlette.templating import Jinja2Templates

_dir = os.path.join(os.path.dirname(__file__), 'templates')
templates = Jinja2Templates(directory=_dir)
