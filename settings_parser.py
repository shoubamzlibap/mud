# settings_parser.py
"""
A generic way to parse a module with globals and return
an object with those globals as attributes.

"""

#from ...settings import settings

class SettingsParser(object):
    """Parse a module and turn globals into attributes"""
    
    def __init__(self, settings_module=None):
        """
        Turn globals from a module into object attributes
        
        settings_module: tuple, (relative module path, module name)
                                 path should be relative to this file
        """
        # check if settings_module was defined, define default
        if not settings_module:
            settings_module = ('...settings', 'settings')
        exec 'from ' + settings_module[0] + ' import ' + settings_module[1] + ' as settings'
        for key,value in settings.__dict__.iteritems():
            if not key.startswith('__'):
                self.__dict__[key] = value

