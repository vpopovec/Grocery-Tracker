import pytest
from main import Receipt


@pytest.fixture(scope='session')
def receipt_lidl():
    receipt = Receipt(f_name='lidl_close.jpg')
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    return receipt


@pytest.fixture(scope='session')
def receipt_lidl2():
    receipt = Receipt(f_name='lidl_bj2.jpeg')
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    return receipt


@pytest.fixture(scope='session')
def receipt_yeme():
    receipt = Receipt(f_name='yeme2.jpg')
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    return receipt


@pytest.fixture(scope='session')
def receipt_yeme2():
    receipt = Receipt(f_name='yeme1.jpg')
    items = receipt.preprocess_items()
    receipt.process_grocery_list(items)
    return receipt


@pytest.mark.parametrize("receipt,expected", [
    ("receipt_lidl", 'lidl'),
    ("receipt_lidl2", 'lidl'),
    ("receipt_yeme", 'yeme'),
    ("receipt_yeme2", 'yeme')
])
def test_correct_shop(receipt, expected, request):
    receipt = request.getfixturevalue(receipt)
    assert receipt.shop == expected


@pytest.mark.parametrize("receipt,expected", [
    ("receipt_lidl", 9.78),
    ("receipt_lidl2", 8.69),
    ("receipt_yeme", 7.77),
    ("receipt_yeme2", 23.34)
])
def test_correct_total(receipt, expected, request):
    receipt = request.getfixturevalue(receipt)
    assert receipt.total == expected


@pytest.mark.parametrize("receipt,expected", [
    ("receipt_lidl", "21-05-2023 16:43:23"),
    ("receipt_lidl2", "23-05-2023 08:20:05"),
    ("receipt_yeme", "22-05-2023 18:10:25"),
    ("receipt_yeme2", "28-05-2023 17:55:03")
])
def test_correct_date(receipt, expected, request):
    receipt = request.getfixturevalue(receipt)
    assert receipt.shopping_date == expected


@pytest.mark.parametrize("receipt,correct_items", [
    ("receipt_lidl", [
        {'name': 'Toastový chlieb', 'amount': 1, 'final_price': 1.86},
        {'name': 'Proteín. pud. van.', 'amount': 1, 'final_price': 1.71},
        {'name': 'Arašidová tyčinka', 'amount': 1, 'final_price': 0.0},
        {'name': 'Kávová tyčinka', 'amount': 1, 'final_price': 0.45},
        {'name': 'Kečup jemný', 'amount': 1, 'final_price': 1.49},
        {'name': 'Paprikáš 200g', 'amount': 1, 'final_price': 1.89},
        {'name': 'Prot.pud. Cokoláda', 'amount': 1, 'final_price': 1.19},
        {'name': 'Dusená šunka', 'amount': 1, 'final_price': 1.19}
    ]),
    ("receipt_lidl2", [
        {'name': 'Kakaový rez', 'amount': 1, 'final_price': 0.0},
        {'name': 'Van Zmll 2 S mand!', 'amount': 1, 'final_price': 4.49},
        {'name': 'Wrapy celozrnne', 'amount': 1, 'final_price': 1.49},
        {'name': 'Banany', 'amount': 1.182, 'final_price': 1.52},
        {'name': 'Tr cukor prír', 'amount': 1, 'final_price': 1.19}
    ]),
    ("receipt_yeme", [
        {'name': 'Kuracie stehna Prém.', 'amount': 0.432, 'final_price': 3.62},
        {'name': 'BIO tela pre najmens', 'amount': 0.104, 'final_price': 4.15}
    ]),
    ("receipt_yeme2", [
        {'name': 'MOJITO 4,7% 330m1', 'amount': 1, 'final_price': 1.69},
        {'name': 'Sencha Raspb. 250m1', 'amount': 1, 'final_price': 2.49},
        {'name': 'Kuracie prsia Prém', 'amount': 0.598, 'final_price': 7.12},
        {'name': 'Kuracie prsia Prém', 'amount': 0.526, 'final_price': 6.26},
        {'name': 'Kuracie prsia Prém.', 'amount': 0.486, 'final_price': 5.78}
    ])
])
def test_processes_all_groceries(receipt, correct_items, request):
    receipt = request.getfixturevalue(receipt)
    assert all([item in receipt.grocery_list for item in correct_items])
