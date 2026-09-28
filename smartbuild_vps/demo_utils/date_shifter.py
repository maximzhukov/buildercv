import pandas as pd
import argparse
import os

def shift_dates(input_file, output_file, days_to_shift):
    """
    Сдвигает даты в CSV файле на заданное количество дней (вперед или назад) 
    и сохраняет/перезаписывает результат.
    """
    try:
        # 1. Читаем исходный файл в память
        df = pd.read_csv(input_file, sep=';')
        
        date_columns = ['Начало работ', 'Окончание работ']
        
        # 2. Сдвигаем даты
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], format='%d.%m.%Y', errors='coerce')
            df[col] = df[col] + pd.Timedelta(days=days_to_shift)
            df[col] = df[col].dt.strftime('%d.%m.%Y')
            
        # 3. Записываем результат по указанному пути (старый файл будет перезаписан)
        df.to_csv(output_file, sep=';', index=False)
        
        direction = "назад" if days_to_shift < 0 else "вперед"
        
        # Проверяем, перезаписали мы файл или создали новый, чтобы вывести красивое сообщение
        if os.path.abspath(input_file) == os.path.abspath(output_file):
            print(f"Успех! Даты сдвинуты на {abs(days_to_shift)} дней {direction}.")
            print(f"Исходный файл ПЕРЕЗАПИСАН: {output_file}")
        else:
            print(f"Успех! Даты сдвинуты на {abs(days_to_shift)} дней {direction}.")
            print(f"Результат сохранен в новый файл: {output_file}")
            
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сдвиг дат в CSV файле с возможностью перезаписи.")
    
    # Входной файл (если не указать, ищет plan.csv в текущей папке)
    parser.add_argument("-i", "--input", default="plan.csv", 
                        help="Путь к входному CSV файлу (по умолчанию plan.csv)")
    
    # Выходной файл (если не указать, скрипт перезапишет входной файл)
    parser.add_argument("-o", "--output", default=None, 
                        help="Путь для сохранения результата. Если не указан, исходный файл будет перезаписан.")
    
    # Количество дней
    parser.add_argument("-d", "--days", type=int, required=True, 
                        help="Количество дней для сдвига (используйте отрицательные числа для обратного отсчета, например -5)")
    
    args = parser.parse_args()
    
    # Если пользователь не указал выходной файл (-o), используем путь входного файла (-i) для перезаписи
    final_output = args.output if args.output else args.input
    
    shift_dates(args.input, final_output, args.days)