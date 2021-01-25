from telegram.ext import Updater, CommandHandler
import telegram
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import pymongo
import threading
import time
import re
from conf import EMAIL, PASSWD, TOKEN, DBNAME, COLNAME, TIMEOUT, ADMINS

def doLogin(driver):
    login_button = driver.find_element_by_xpath('//button[contains(text(), "ورود به حساب کاربری")]')
    login_button.click()
    email_input = driver.find_element_by_id('signinform-login-input')
    email_input.clear()
    email_input.send_keys(EMAIL)
    passwd_input = driver.find_element_by_id('signinform-password-input')
    passwd_input.clear()
    passwd_input.send_keys(PASSWD)
    button_confirm_div = driver.find_element_by_xpath('//div[contains(@class, "button-confirm")]')
    login_submit = button_confirm_div.find_element_by_tag_name('button')
    while True:
        try:
            login_submit.click()
            break
        except ElementClickInterceptedException:
            print('Error: disable button ! waiting ...')

def checkHaveCharge(driver):
    try:
        bet_error_li = driver.find_element_by_xpath('//span[contains(text(), "موجودی کافی نیست")]/ancestor::li[1]')
    except NoSuchElementException:
        return True
    if 'ng-hide' in bet_error_li.get_attribute('class'):
        return True
    return False

def checkLogedIn(driver):
    try:
        signin_reg_li = driver.find_element_by_xpath('//div[@id="signin-reg-buttons"]/ancestor::li[1]')
    except NoSuchElementException:
        return True
    if 'ng-hide' in signin_reg_li.get_attribute('class'):
        return True
    return False

def closeSlider(driver):
    try:
        slider_block = driver.find_element_by_id('block-slider-container')
    except NoSuchElementException:
        return
    if 'ng-hide' not in slider_block.get_attribute('class'):
        slider_close_button = slider_block.find_element_by_xpath('//div[contains(@class, "close-slider-button-j")]')
        slider_close_button.click()

def make_bet(driver, option_index, amount):

    #### LOGIN ####
    if not checkLogedIn(driver):
        doLogin(driver)
        time.sleep(TIMEOUT) # timeout
        closeSlider(driver)
    #### LOGIN ####

    try:
        option_element = driver.find_element_by_xpath("//div[@data-title='مجموع گل‌ها']/ancestor::div[1]//div[@title='کم‌تر از  (%s)']" % option_index)
    except NoSuchElementException:
        print('Error: option %s element not found !' % option_index)
        return None
    option_element.click()

    pishbini_tab = driver.find_element_by_xpath('//div[@title="پیش‌بینی"]')
    pishbini_tab.click()

    amount_element = driver.find_element_by_id('express-bet-input')
    amount_element.clear()
    amount_element.send_keys(amount)

    if not checkHaveCharge(driver):
        for admin_cid in ADMINS:
                tel_bot.sendMessage(chat_id=admin_cid, text="موجودی حساب کافی نیست، سریعتر شارژ کنید !")
    while not checkHaveCharge(driver):
        time.sleep(TIMEOUT)

    pishbini_submit = driver.find_element_by_xpath('//div[contains(@class, "button-view-contain-v3")]')
    pishbini_submit.click()
    
    return True

def checkGameEnded(driver):
    game_time_c = driver.find_element_by_xpath('//div[contains(@class, "current-game-info-line")]')
    game_time = game_time_c.find_elements_by_tag_name('span')[-1].text
    return game_time == '90'

def chackGameIsUnavailable(driver, game_pk):
    return game_pk not in driver.current_url

def checkGameStarted(driver):
    try:
        live_container = driver.find_element_by_xpath('//div[contains(@class, "live-game-container")]')
    except NoSuchElementException:
        return False
    el_class = live_container.get_attribute('class')
    if el_class is None or 'ng-hide' in el_class:
        return False
    try:
        live_container.find_element_by_xpath('//span[contains(text(), "شروع نشده")]')
        return False
    except NoSuchElementException:
        return True

def getTotalGoals(driver):
    return sum([int(score_el.find_element_by_tag_name('i').text) for score_el in driver.find_elements_by_class_name('score-total')])

def newTab(driver, url="about:blank"):
    driver.execute_script('''window.open("%s","_blank");''' % url)
    driver.switch_to.window(driver.window_handles[-1])

def bet_thread():
    driver = webdriver.Chrome('chromedriver.exe')
    while True:
        for game in games_col.find():
            if game['tab'] is None:
                newTab(driver, game['url'])
                games_col.update_one({'_id': game['_id']}, {'$set': {'tab': driver.current_window_handle}})
            else:
                driver.switch_to.window(game['tab'])
            if game['status'] == 'waiting':
                if checkGameStarted(driver):
                    if make_bet(driver, 1.5, game['amount']):
                        games_col.update_one({'_id': game['_id']}, {'$set': {'status': 'live'}})
            elif game['status'] == 'live':
                if chackGameIsUnavailable(driver, game['game_pk']):
                    games_col.update_one({'_id': game['_id']}, {'$set': {'status': 'unavailable'}})
                elif checkGameEnded(driver):
                    games_col.delete_one({'_id': game['_id']})
                    driver.close() # close current tab
                elif getTotalGoals(driver) > game['option_index']:
                    new_amount = str(int(int(game['amount']) * 1.5))
                    new_option_index = game['option_index'] + 1
                    if make_bet(driver, new_option_index, new_amount):
                        games_col.update_one({'_id': game['_id']}, {'$set': {'option_index': new_option_index}})
                        games_col.update_one({'_id': game['_id']}, {'$set': {'amount': new_amount}})
            elif game['status'] == 'unavailable':
                if not chackGameIsUnavailable(driver, game['game_pk']):
                    games_col.update_one({'_id': game['_id']}, {'$set': {'status': 'live'}})


def add_game(update, context):
    cid = update.message.chat_id
    if cid not in ADMINS:
        return
    text = update.message.text
    game_link, amount = text.split(' ')[1:]
    if not game_link.endswith('&lang=fas'):
        game_link += '&lang=fas'
    game_link = game_link.replace('type=1', 'type=0')
    game_pk = re.findall(r'game=(.*)&', game_link)[0]
    games_col.insert_one({
        'url': game_link,
        'amount': amount,
        'option_index': 1.5,
        'status': 'waiting',
        'tab': None,
        'game_pk': game_pk
    })
    context.bot.sendMessage(chat_id=cid, text="Added successfully.")


def start(update, context):
    cid = update.message.chat_id
    if cid not in ADMINS:
        return
    context.bot.sendMessage(chat_id=cid, text='welcome!')


if __name__ == '__main__':

    mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
    games_col = mongo_client[DBNAME][COLNAME]

    tel_bot = telegram.Bot(TOKEN)
    updater = Updater(bot=tel_bot)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('addGame', add_game))

    b_thread = threading.Thread(target=bet_thread)
    b_thread.start()

    updater.start_polling()
    updater.idle()