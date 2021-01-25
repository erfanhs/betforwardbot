from selenium import webdriver
from bot import make_bet, checkGameEnded, chackGameIsUnavailable, checkGameStarted, getTotalGoals, newTab, checkLogedIn
import time 

TIMEOUT = 5

url = 'https://www.betforward.com/#/sport/?type=0&region=1850001&competition=560&sport=1&game=17468025&lang=fas'

driver = webdriver.Chrome('chromedriver.exe')

driver.get(url)


def test_checkLogedIn(driver, res):
    result = checkLogedIn(driver)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')

def test_make_bet(driver, option_index, amount, res):
    time.sleep(TIMEOUT)
    result = make_bet(driver, option_index, amount)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')

def test_checkGameEnded(driver, res):
    time.sleep(TIMEOUT)
    result = checkGameEnded(driver)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')

def test_chackGameIsUnavailable(driver, game_pk, res):
    time.sleep(TIMEOUT)
    result = chackGameIsUnavailable(driver, game_pk)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')

def test_checkGameStarted(driver, res):
    time.sleep(TIMEOUT)
    result = checkGameStarted(driver)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')

def test_getTotalGoals(driver, res):
    time.sleep(TIMEOUT)
    result = getTotalGoals(driver)
    if result == res:
        print('Ok.')
    else:
        print('Faild!')


# test_checkLogedIn(driver, False)
# test_make_bet(driver, 1.5, '10000', True)
# test_checkGameEnded(driver, True)
# test_chackGameIsUnavailable(driver)
# test_checkGameStarted(driver, True)
# test_getTotalGoals(driver, 3)