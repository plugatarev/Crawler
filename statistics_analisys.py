import csv
import matplotlib.pyplot as plt
from src.settings import STATISTICS_FILENAME 

# Чтение данных из CSV файла
with open(STATISTICS_FILENAME, 'r') as f:
    reader = csv.reader(f)
    
    # Получение данных из первой строки (имена колонок)
    headers = next(reader)
    
    # Список для хранения значений оси X
    x_values = []
    
    # Словарь для хранения функций
    y_functions = {}
    
    for row in reader:
        x_value = float(row[0])
        x_values.append(x_value)
        
        for i in range(1, 6):
            header = headers[i]
            
            if header not in y_functions:
                y_functions[header] = []
                
            y_function = float(row[i])
            y_functions[header].append(y_function)

# Создание графика
plt.figure()
for key in y_functions:
    plt.plot(x_values, y_functions[key], label=key)

plt.legend()
plt.show()