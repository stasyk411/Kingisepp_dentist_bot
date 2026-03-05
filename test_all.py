import subprocess
import sys

print("=" * 50)
print("ЗАПУСК ВСЕХ ТЕСТОВ")
print("=" * 50)

# Используем тот же Python, что и в текущем окружении
python_exe = sys.executable

print(f"\n1. ТЕСТ БАЗЫ ДАННЫХ:")
subprocess.run([python_exe, "test_slots.py"])

print(f"\n2. ТЕСТ КЛИЕНТА:")
subprocess.run([python_exe, "test_client.py"])

print(f"\n3. ТЕСТ АДМИНКИ:")
subprocess.run([python_exe, "test_admin.py"])