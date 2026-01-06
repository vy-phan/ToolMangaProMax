import sys
import os
import importlib.util
import inspect
from pathlib import Path

def get_scrapers_directory():
    """
    Xác định vị trí thư mục 'scrapers'.
    """
    if getattr(sys, 'frozen', False):
        # Đang chạy file .exe
        application_path = Path(sys.executable).parent
    else:
        # Đang chạy code python
        application_path = Path(__file__).resolve().parent.parent.parent
    
    scrapers_dir = application_path / "scrapers"
    return scrapers_dir

def load_scrapers():
    """
    Quét và load các class Scraper từ thư mục bên ngoài
    """
    scrapers_dir = get_scrapers_directory()
    scrapers = {}

    # 1. Tạo thư mục nếu chưa có
    if not scrapers_dir.exists():
        try:
            scrapers_dir.mkdir(parents=True, exist_ok=True)
            # Tạo file __init__.py để biến nó thành package (quan trọng cho import)
            (scrapers_dir / "__init__.py").touch()
        except Exception as e:
            print(f"[Loader] Lỗi tạo folder: {e}")
            return {}

    # 2. [QUAN TRỌNG] Thêm thư mục scrapers vào sys.path
    # Để các plugin có thể import lẫn nhau (ví dụ import base)
    sys.path.insert(0, str(scrapers_dir))

    print(f"[Loader] Đang quét tại: {scrapers_dir}")

    py_files = list(scrapers_dir.glob("*.py"))

    for file_path in py_files:
        module_name = file_path.stem 
        
        if module_name.startswith("__") or module_name == "base":
            continue

        try:
            # Load module động
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Quét class trong module
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    
                    # Kiểm tra Duck Typing (Có đủ hàm cần thiết)
                    if (inspect.isclass(attribute) and 
                        hasattr(attribute, 'name') and 
                        hasattr(attribute, 'domain') and 
                        hasattr(attribute, 'get_images') and
                        attribute_name != 'BaseScraper'):
                        
                        try:
                            instance = attribute()
                            scrapers[instance.name] = instance
                            print(f"  [OK] Load thành công: {instance.name}")
                        except Exception as e:
                            print(f"  [ERROR] Lỗi khởi tạo {attribute_name}: {e}")

        except Exception as e:
            # Lỗi này thường do import sai trong file plugin
            print(f"  [CRITICAL] Không thể load file {file_path.name}: {e}")
            
    return scrapers