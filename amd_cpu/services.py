# amd_cpu/services.py
import os
from django.conf import settings
import xlrd
from .models import AMDCPU


class AMDCPUService:
    _cpus = None  # In-memory storage

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
    def search_cpus(cls, search_term):
        cpus = cls.load_cpus()
        return [cpu for cpu in cpus if cpu.matches_search(search_term)]