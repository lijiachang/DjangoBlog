# amd_cpu/services.py
import json
import os
from django.conf import settings
import xlrd
from .models import AMDCPU


class AMDCPUService:
    _cpus = None  # In-memory storage
    _benches = None

    @classmethod
    def load_cpus(cls):
        if cls._cpus is not None:
            return cls._cpus

        cpus = []
        excel_path = os.path.join(settings.BASE_DIR, 'amd_cpu', 'data', 'AMD处理器ES规格表.xls')

        try:
            # Open the workbook
            workbook = xlrd.open_workbook(excel_path)
            # Get the first sheet
            sheet = workbook.sheet_by_index(0)

            # Skip the header row
            for row_idx in range(1, sheet.nrows):
                row_values = []
                for col_idx in range(sheet.ncols):
                    cell_value = sheet.cell_value(row_idx, col_idx)
                    row_values.append(cell_value)

                if not row_values or all(not val for val in row_values):
                    continue

                cpus.append(AMDCPU(row_values))

        except Exception as e:
            print(f"Error loading Excel file: {e}")

        cls._cpus = cpus
        return cpus

    @classmethod
    def load_benches(cls):
        if cls._benches is not None:
            return cls._benches

        _benches = []
        excel_path = os.path.join(settings.BASE_DIR, 'amd_cpu', 'data', 'cpu_bench.json')

        try:
            _benches = json.load(open(excel_path))
            # [{'id': '5493', 'pai_ming': 1, 'ming_cheng': 'AMD Ryzen Threadripper PRO 7995WX', 'shu_zhi': '158518', 'bai_fen_bi': 100},
        except Exception as e:
            print("Error loading cpu_bench file: %s" % e)

        cls._benches = _benches
        return _benches

    @classmethod
    def search_cpus(cls, search_term):
        cpus = cls.load_cpus()
        benches = cls.load_benches()
        result =  [cpu for cpu in cpus if cpu.matches_search(search_term)]
        for cpu in result:
            for bench in benches:
                cpu_name = cpu.name.replace('™', '') # AMD Ryzen™ 7 7840U -> AMD Ryzen 7 7840U
                # print(cpu_name)
                if cpu_name in bench['ming_cheng']:
                    cpu.add_cpu_bench(bench['shu_zhi'])
                    break

        return result