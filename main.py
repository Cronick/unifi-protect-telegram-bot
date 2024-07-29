import requests
import time
import telebot
from loguru import logger
from config import config
from tinydb import TinyDB, Query

db = TinyDB('video_history.json')
search = Query()

requests.packages.urllib3.disable_warnings()

# Start Telegram Bot
telegram_bot = telebot.TeleBot(config.telegram.bot_token, parse_mode=None)

if config.telegram.startup_msg:
    telegram_bot.send_message(config.telegram.chat_id, 'Bot starting up.')

def getCameraList(session) -> list:
    devices = session.get(f"{config.unifi.hostname}/proxy/protect/api/bootstrap", verify=False).json()
    camerasIds = []
    camerasName = []
    for camera in devices['cameras']:
        camerasIds.append(camera['id'])
        camerasName.append(camera['name'])
    return camerasIds, camerasName

def getCameraName(session, camera_id) -> str:
    devices = session.get(f"{config.unifi.hostname}/proxy/protect/api/bootstrap", verify=False).json()
    for camera in devices['cameras']:
        if camera['id'] == camera_id:
            return camera['name']
    return ""

def checkNetworkDevices(session) -> str:
    devices = session.get(f"{config.unifi.hostname}/proxy/network/v2/api/site/default/clients/active", params={ 'includeTrafficUsage': False, 'includeUnifiDevices': False}, verify=False).json()

    count = 0
    device_msg = ""
    for device in devices:
        if device["mac"] in config.network.devices:
            count += 1
            device_msg += f"{device['display_name']} & "

    if count > 0:
        return device_msg.rstrip(" & ")
    else:
        return ""

def main():
    session = requests.Session()
    login = session.post(f"{config.unifi.hostname}/api/auth/login", data={'username': config.unifi.username, 'password': config.unifi.password, 'remember': True}, verify=False)
    if login.status_code!= 200:
        logger.error("Failed to login to unifi controller.")
        logger.error(f"Error message from Unifi: {login.json()}")
        exit()

    while True:

        cameraIds, cameraNames = getCameraList(session)
        logger.info(f"Checking latest video motions on cameras: {', '.join(cameraNames)}")
        
        for camera in cameraIds:

            # Get Latest motions detected.
            latestMotionsDetected = session.get(f"{config.unifi.hostname}/proxy/protect/api/events", params={ 'allCameras': True, 'cameras': camera, 'limit': 5, 'orderDirection': 'DESC', 'types': 'motion'}, verify=False)

            # Check if Motion Info is received.
            if latestMotionsDetected.status_code != 200:
                logger.warning('Received a error while fetting Unifi Events.')
                logger.warning(f"Error message from Unifi: {latestMotionsDetected.text}")
                main()

            # Check if we have a new video, we have not sent previously.
            for video in latestMotionsDetected.json():

                if db.search(Query().id == video['id']):
                    continue

                logger.info(f"Found new video: {video['id']} on Camera: {getCameraName(session, camera)}")

                # If devices is detected on Wifi, then no need to send a message.
                devices = checkNetworkDevices(session)
                if devices != "":
                    db.insert({'id': video['id']})
                    logger.info(f"Found following device(s) on Wifi: {devices}, so no need to send video.")
                    continue

                file_motion = session.get(f'{config.unifi.hostname}/proxy/protect/api/video/export', params={'camera': camera, 'channel': 0, 'start': video['start'], 'end': video['end']}, verify=False)
                if file_motion.status_code != 200:
                    logger.warning('Download video failed. Will retry again in next check.')
                    continue

                try:
                    logger.info('Download done, so lets send it to Telegram channel.')
                    telegram_bot.send_video(config.telegram.chat_id, file_motion.content, caption=f"Motion detected on {getCameraName(session, camera)}.")
                    logger.info(f"Video {video['id']} sent.")
                    db.insert({'id': video['id']})
                
                except Exception:
                    logger.error('Failed to send video to Telegram. Maybe a network issue?')

        time.sleep(config.unifi.check_interval)

if __name__ == "__main__":
    main()