import errno
import os
import sys
from pydantic import BaseModel, validator

class FilePath(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, field):
        if not cls.is_pathname_valid(value):
            raise ValueError(f'Invalid file path: {value}')        
        return value

    @staticmethod
    def is_pathname_valid(pathname: str) -> bool:
        # from stackoverflow
        ERROR_INVALID_NAME = 123
        try:
            if not isinstance(pathname, str) or not pathname:
                return False

            _, pathname = os.path.splitdrive(pathname)

            root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
                if sys.platform == 'win32' else os.path.sep
            assert os.path.isdir(root_dirname)

            root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

            for pathname_part in pathname.split(os.path.sep):
                try:
                    os.lstat(root_dirname + pathname_part)
                except OSError as exc:
                    if hasattr(exc, 'winerror'):
                        if exc.winerror == ERROR_INVALID_NAME:
                            return False
                    elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                        return False
        except TypeError:
            return False
        else:
            return True
        
if __name__ == "__main__":
    class FilePathModel(BaseModel):
        file_path: FilePath
    
    # Example usage
    try:
        file_path_model = FilePathModel(file_path="\\valid\\path\\file.txt")
        print("The file path is valid.")
    except ValueError as e:
        print(f"Error: {e}")