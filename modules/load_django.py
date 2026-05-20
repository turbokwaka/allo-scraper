import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'allo_ua')))

os.environ['DJANGO_SETTINGS_MODULE'] = 'allo_ua.settings'

django.setup()
