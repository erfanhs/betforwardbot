from telegram.ext import Updater, CommandHandler
import telegram
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import pymongo
import threading
import time
import re

def make_bet(driver, option_index, amount):
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

    pishbini_submit = driver.find_element_by_xpath('//div[contains(@class, "button-view-contain-v3")]')
    pishbini_submit.click()
    
    return True

def checkGameEnded(driver):
    game_time_c = driver.find_element_by_xpath('//div[contains(@class, "current-game-info-line")]')
    game_time = game_time_c.find_elements_by_tag_name('span')[-1].text
    return game_time == '90'
    # try:
    #     game_finished = driver.find_element_by_xpath('//p[contains(@class, "game-finished")]')
    # except NoSuchElementException:
    #     return False
    # if 'ng-hide' in game_finished.get_attribute('class'):
    #     return False
    # return True

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
    context.bot.sendMessage(chat_id=update.message.chat_id, text='welcome!')


if __name__ == '__main__':

    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["betForward"]
    games_col = mydb["games"]

    TOKEN = '1559806560:AAF6iyl8NhEoeycJPSFx2MbM9quE7SYX9-M'
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('addGame', add_game))

    b_thread = threading.Thread(target=bet_thread)
    b_thread.start()

    updater.start_polling()
    updater.idle()