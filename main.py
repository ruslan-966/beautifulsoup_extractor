from bs4 import BeautifulSoup
import copy
import glob
import os
import pandas as pd
from model_param import *


def soup_find_all_teg_class(soup, teg, cls):
    lst = []
    for t in soup.find_all(teg, class_=cls):
        lst.append(t.text)
    return lst


def data_comb(a, b):
    comb = []
    j = 0   # Индекс для b
    for i in range(len(a)):
        if a[i].find(b[j]) <= -1:  # элемент списка а не содержит в себе элемент списка b
            comb.append('Not')
        else:
            comb.append(b[j])
            j += 1
            if j >= len(b):                         # Счетчик больше номера последнего элемента в списке b
                comb += ['Not'] * (len(a) - i - 1)     # Увеличиваем comb до размера a, заполнив элементами Not
                break
    return comb


def advertising_killer(info, store):   # Удаляет рекламу (у рекламы отсутствует склад - продавец)
    comb = []
    for card_1 in info:
        for card_2 in store:
            if card_1.find(card_2) >= 1:  # Отдельный элемент списка содержит имя класса
                comb.append(card_1)
                break
    return comb


def make_decimal_from_string(string):
    result = 0
    if string:
        new_str = ''.join([i for i in string if i.isdigit() or i == ','])
        [num, dec] = new_str.rsplit(',')
        result += int(num.replace(' ', ''))
        result += (int(dec) / 100)
    return result


def bs_doing():
    total_name = []
    total_price = []
    total_store = []
    total_delivery = []
    # Считаем количество файлов в директории, содержащем html страницы:
    curr_dir = os.getcwd()
    dir_path = f'{curr_dir}\\{SITE_DATA_FOLDER}'
    html_list_counter = len(glob.glob1(dir_path, "*.html"))
    if html_list_counter <= 1:  # Проверяем количество файлов для распарсивания данных. если их мало - выходим
        return [[0], [0], [0], [0]]
    # Начинаем парсить данные:
    count = 1
    while count < html_list_counter:
        file_name = f'{dir_path}\\page_source_{count}.html'
        with open(file_name, encoding='utf-8') as file:
            src = file.read()
        soup = BeautifulSoup(src, 'lxml')
        # # Сохраняем страницу в презентабельном виде (использовать при отладке)
        # if count == 27:
        #     with open('aaa.html', "w", encoding="utf-8") as f:
        #         f.write(soup.prettify())
        # Вытаскиваем из страницы сайта информацию (Объявление о продаже,
        #                                           цену еденицы товара,
        #                                           наименование продавца,
        #                                           стоимость доставки)
        product_delivery = []
        common_info = soup_find_all_teg_class(soup, "div", "product-snippet_ProductSnippet__content__tusfnx")
        product_name = soup_find_all_teg_class(soup, "div", "product-snippet_ProductSnippet__name__tusfnx")
        product_price = soup_find_all_teg_class(soup, "div", "snow-price_SnowPrice__mainM__1ehyuw")
        product_store = soup_find_all_teg_class(soup, "div", "product-snippet_ProductSnippet__caption__tusfnx")

        # Выделяем тип доставки. ключи поиска отличаются в зависимости от обрабатываемой страницы:
        if count == 1:
            for tag in soup.find_all("div", class_="snow-price_SnowPrice__freeDelivery__1ehyuw", style=""):
                product_delivery.append(tag.text)
        else:
            for tag in soup.find_all("div", class_="snow-price_SnowPrice__freeDelivery__1ehyuw",
                                     style="display:inline-block"):
                product_delivery.append(tag.text)

        # for name, price in zip(product_name, product_price):    # промежуточный вывод данных
        #     print('=' * 50)
        #     print(name, ' | ', price, ' | ')

        # Причесываем полученные данные: 1.Из карточек с товаром - удаляем те,
        # у которых отсутствует наименование продавца.
        # 2. Заполняем возможные пропуски в объявлении, цене, наименовании продавца,
        # что бы номера в списках соответствовали номерам карточки товара.
        common_info = copy.deepcopy(advertising_killer(common_info, product_store))
        product_name = copy.deepcopy(data_comb(common_info, product_name))
        product_price = copy.deepcopy(data_comb(common_info, product_price))
        product_store = copy.deepcopy(data_comb(common_info, product_store))
        product_delivery = copy.deepcopy(data_comb(common_info, product_delivery))
        # Сводим в единый список со всех страниц, содержащих объявления о товаре,
        #                                                               цены на товар,
        #                                                               продавцов,
        #                                                               доставку
        total_name.extend(product_name)
        total_price.extend(product_price)
        total_store.extend(product_store)
        total_delivery.extend(product_delivery)
        print('Текущее значение счетчика страниц: {0}'.format(count))
        count += 1
    # Конвертируем список цен из string в числовые значения:
    prom_price = []
    for string in total_price:
        prom_price.append(make_decimal_from_string(string))
    total_price = copy.deepcopy(prom_price)
    # Конвертируем способы доставки (total_delivery) из
    # строкового списка в логический список(там встречается только два значения: бесплатная доставка и договоренность):
    prom_delivery = []
    for string in total_delivery:
        if string == 'Not':
            prom_delivery.append(False)
        else:
            prom_delivery.append(True)
    total_delivery = copy.deepcopy(prom_delivery)
    # Если установлен ключ, записываем результат в файл:
    if SAFE_COMMON_RESULT_KEY:
        # Формируем DataFrame:

        common_result_pd = pd.DataFrame(list(zip(total_name, total_price, total_store, total_delivery)),
                                        columns=['product_description', 'product_price',
                                                 'product_store', 'product_delivery'])
        file_name = f'{curr_dir}\\{TOTAL_DATA_FILE_NAME}'
        common_result_pd.to_csv(file_name, encoding='cp1251', errors='replace', index=False)
    # Возвращаем выделенные данные
    return [total_name, total_price, total_store, total_delivery]


def main():
    bs_doing()
    # list_a = bs_doing()
    # Используется для отладки:
    # for name, price, store, delivery in zip(list_a[0], list_a[1], list_a[2], list_a[3]):
    #     print('*' * 50)
    #     print(name, ' | ', price, ' | ', store, ' | ', delivery)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
    finally:
        print('Программа bs_python расчет закончила.')
