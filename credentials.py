import os
import sys
from pathlib import Path
from consts import CREDENTIALS_FILE_NAME

class Credentials:
    """
    10/24/2025. Load credentials once from credentials file and expose them as properties. Keep _ENVVARS in sync with members in credentials file.
    """

    # 10/24/2025. Class-level constants listing expected environment variables.
    _ENVVARS = ("SHOPIFY_API_KEY", "SHOPIFY_API_KEY_RW", "SHOPIFY_PASSWORD", "SHOPIFY_PASSWORD_RW", "SHOPIFY_API_KEY_2",
                "SHOPIFY_PASSWORD_2", "CC_REFRESH_TOKEN", "CC_CLIENT_ID", "CC_CLIENT_SECRET","CC_NEAF_DOOR_PRIZE_REGISTRATION_LIST_ID")

    # 10/24/2025. Class-level cache of env values; loaded once per process.
    _values = {}
    error = ''
    _full_path = ''

    @staticmethod
    def _make_prop(envvar):
        def getter(self):
            return Credentials._values[envvar]
        return property(getter)

    @classmethod
    def _attach_properties(cls):
        """10/28/2025. Private. Attach properties for each credential to the class. Called only from __init__()."""
        for name in cls._ENVVARS:
            setattr(cls, name, cls._make_prop(name))
        return

    def __init__(self):
        """
        10/24/2025. On first instantiation, load all required credentials from credentials file. If any are missing, raise an exception.
                    Ensure all properties exist before __init__ returns so callers can access attributes immediately.
        """

        if not Credentials._values:

            # 12/8/2025. it is assumed the credentials file is in same folder as project
            filename_only = os.path.basename(__file__)
            Credentials._full_path = __file__.replace(filename_only,CREDENTIALS_FILE_NAME)
            path = Path(Credentials._full_path)
            if not path.exists():
                Credentials.error = f"Credentials file of {path} does not exist."
                raise FileNotFoundError(Credentials.error)

            credDict = {}
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line[0] != '#':
                        # 12/15/2025. if line starts with # its a comment so skip.
                        line_toks = line.split('=')
                        if len(line_toks)==2:
                            if '\'' in line or '"' in line:
                                Credentials.error = f"Invalid line found in credentials file loaded from {path}\n{line} is invalid. Quote characters not allowed."
                                raise RuntimeError(Credentials.error)
                            credDict[line_toks[0].strip()] = line_toks[1].strip('\n').strip()
                        else:
                            Credentials.error = f"Invalid line found in credentials file loaded from {path}\n{line} is invalid. It's not a comment but its not is form <key>=<value>."
                            raise RuntimeError(Credentials.error)

            if len(credDict) != len(Credentials._ENVVARS):
                Credentials.error = f"Number of distinct credentials loaded from {path} is {len(credDict)} but number of items in Credentials._ENVVARS is {len(Credentials._ENVVARS)}." +\
                    "\nThey must be equal."
                raise RuntimeError(Credentials.error)

            missing = []
            for key in Credentials._ENVVARS:
                val = credDict.get(key)
                if val is None:
                    missing.append(key)
                else:
                    Credentials._values[key] = val
            if missing:
                cnt = len(Credentials._values)
                Credentials._values.clear()
                Credentials.error = f"Failed constructing Credentials object. Missing the following required credentials from file {path}:\n{', '.join(missing)}" +\
                                    f"\nClearing out the {cnt} credentials that were successfully loaded."
                raise RuntimeError(Credentials.error)

            envvars = Credentials._ENVVARS
            midpoint = len(envvars) // 2
            first_half = ', '.join(envvars[:midpoint])
            second_half = ', '.join(envvars[midpoint:])
            credstr = first_half + '\n' + second_half
            print(f"\nSuccessfully loaded the following {len(Credentials._ENVVARS)} credentials from {Credentials._full_path}.\n{credstr}")
            print('Use these values for all subsequent Credentials object instantiations in this unit of work.\n')

        Credentials._attach_properties()
        return

    def __str__(self):
        """
        10/24/2025. Produce a readable summary of all loaded credentials. Safe to show full values since only trusted users have access to credentials.
        """
        if Credentials.error:
            return Credentials.error
        res = f'Members of Credentials object built from file {Credentials._full_path}:'
        for k,v in Credentials._values.items():
            delim = '\n'
            res += f'{delim}{k} : {v}'
        return res

def test_load_credentials():
    cr = Credentials()
    print(str(cr))
    cr2 = Credentials()
    print('\n'+str(cr2))
    return

if __name__ == "__main__":
    test_load_credentials()