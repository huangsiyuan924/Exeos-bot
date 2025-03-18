import uuid

from curl_cffi import requests
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import Fore, Style, init
import asyncio, json, os, pytz

# 初始化 colorama
init(autoreset=True)

# 设置时区
wib = pytz.timezone('Asia/Jakarta')


class ExeOSBot:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "User-Agent": FakeUserAgent().random,
        }
        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.config = {
            "log_file_path": "exeos-bot.log",
            "liveness_delay": 5000,
            "liveness_interval": 15000,
            "connect_interval": 60000,
        }
        self.nodeId_list = []
        self.email = None
        self.total_ext = 137
    def clear_terminal(self):
        os.system("cls" if os.name == "nt" else "clear")

    def log(self, message, account_index="", log_type="INFO"):
        account_index = self.email
        timestamp = datetime.now().astimezone(wib).strftime("%x %X %Z")
        colored_message = f"{Fore.CYAN}[{timestamp}]{Style.RESET_ALL} [{account_index}] "

        if log_type == "CONNECT":
            colored_message += f"{Fore.GREEN}[CONNECT]{Style.RESET_ALL} {message}"
        elif log_type == "LIVENESS":
            colored_message += f"{Fore.BLUE}[LIVENESS]{Style.RESET_ALL} {message}"
        elif log_type == "STATS":
            colored_message += f"{Fore.MAGENTA}[STATS]{Style.RESET_ALL} {message}"
        elif log_type == "POINTS":
            colored_message += f"{Fore.YELLOW}[POINTS]{Style.RESET_ALL} {message}"
        elif log_type == "ERROR":
            colored_message += f"{Fore.RED}[ERROR]{Style.RESET_ALL} {message}"
        else:
            colored_message += f"{Fore.CYAN}[INFO]{Style.RESET_ALL} {message}"

        print(colored_message)
        with open(self.config["log_file_path"], "a") as log_file:
            log_file.write(f"[{timestamp}] [{log_type}] [{account_index}] {message}\n")

    def welcome(self):
        print(
            f"""
        {Fore.GREEN}Auto Ping {Fore.BLUE}ExeOS - BOT
            """
            f"""
        {Fore.GREEN}Rey? {Fore.YELLOW}<INI WATERMARK>
            """
        )

    def load_accounts(self):
        account_list = []
        if os.path.exists("token.txt"):
            with open("token.txt", "r", encoding="utf-8") as file:
                tokens = file.read().splitlines()
                for token in tokens:
                    if token.strip():
                        account_list.append({"token": token.strip()})
        return account_list

    async def load_proxies(self):
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r", encoding="utf-8") as file:
                self.proxies = [line.strip() for line in file if line.strip()]
        self.log(f"Loaded {len(self.proxies)} proxies.")

    def get_next_proxy_for_account(self, token):
        if token not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.proxies[self.proxy_index]
            self.account_proxies[token] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[token]

    def rotate_proxy_for_account(self, token):
        if not self.proxies:
            return None
        proxy = self.proxies[self.proxy_index]
        self.account_proxies[token] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    async def get_public_ip(self, proxy=None):
        try:
            response = await asyncio.to_thread(
                requests.get,
                "https://api.ipify.org/?format=json",
                proxy=proxy,
                impersonate="safari15_5",
            )
            return response.json().get("ip")
        except Exception as e:
            self.log(f"Failed to get public IP: {e}", log_type="ERROR")
            return None

    async def check_account_info(self, token, proxy=None):
        for i in range(3):
            try:
                headers = {**self.headers, "Authorization": f"Bearer {token}"}
                response = await asyncio.to_thread(
                    requests.get,
                    "https://api.exeos.network/account/web/me",
                    headers=headers,
                    proxy=proxy,
                    impersonate="safari15_5",
                )
                data = response.json().get("data", {})
                self.email = data.get("email")
                points = data.get("points", 0)
                self.nodeId_list = [node['nodeId'] for node in data['networkNodes']]
                referral_points = data.get("referralPoints", 0)
                self.log(
                    f"Total Points: {points} | Referral Points: {referral_points}",
                    log_type="POINTS",
                )
                return data
            except Exception as e:
                self.log(f"Failed to get account info: {e}", log_type="ERROR")
            # return None

    async def check_stats(self, token, extension_id, proxy=None):
        for i in range(3):

            try:
                headers = {**self.headers, "Authorization": f"Bearer {token}"}
                data = {"extensionId": extension_id}
                response = await asyncio.to_thread(
                    requests.post,
                    "https://api.exeos.network/extension/stats",
                    headers=headers,
                    json=data,
                    proxy=proxy,
                    impersonate="safari15_5",
                )
                status = response.json()['status']
                if status == "success": return response.json()
                self.log(f"Liveness {status} for {extension_id}", log_type="LIVENESS")
                # return response.json()
            except Exception as e:
                self.log(f"Failed to check stats: {e}", log_type="ERROR")
                # return None

    async def check_liveness(self, token, extension_id, proxy=None):
        await self.check_stats(token, extension_id, proxy)
        while 1:

            try:
                headers = {**self.headers, "Authorization": f"Bearer {token}"}
                data = {"extensionId": extension_id}
                response = await asyncio.to_thread(
                    requests.post,
                    "https://api.exeos.network/extension/liveness",
                    headers=headers,
                    json=data,
                    proxy=proxy,
                    impersonate="safari15_5",
                )

                status = response.json()['status']
                if status == 'fail':
                    await self.check_stats(token, extension_id, proxy)
                self.log(f"{proxy} Liveness {status} for {extension_id}", log_type="LIVENESS")
                await asyncio.sleep(30)
            except Exception as e:
                self.log(f"Failed to check liveness: {e}", log_type="ERROR")
                # return None

    async def connect_extension(self, token, extension_id, proxy=None):
        for i in range(3):
            try:
                ip = await self.get_public_ip(proxy)
                headers = {**self.headers, "Authorization": f"Bearer {token}"}
                data = {"ip": ip, "extensionId": extension_id}
                response = await asyncio.to_thread(
                    requests.post,
                    "https://api.exeos.network/extension/connect",
                    headers=headers,
                    json=data,
                    proxy=proxy,
                    impersonate="safari15_5",
                )
                self.log(f"Connected {extension_id} from {ip}", log_type="CONNECT")
                return response.json()
            except Exception as e:
                self.log(f"Failed to connect: {e}", log_type="ERROR")

    async def process_accounts(self, token):
        proxy = self.get_next_proxy_for_account(token)
        self.log(f"Using proxy: {proxy}", account_index=token[:10])

        # ip = await self.get_public_ip(proxy)
        # if ip:
        await self.check_account_info(token, proxy)
        while len(self.nodeId_list) < self.total_ext:
            random_uuid = str(uuid.uuid4())
            self.nodeId_list.append(f"node:ext:{random_uuid}")

        tasks = []
        for i in range(self.total_ext):
            extension_id = self.nodeId_list[i]
            if i == 0:
                proxy = self.proxies[0]
            else:
                proxy = self.rotate_proxy_for_account(token)

            tasks.append(asyncio.create_task(self.connect_extension(token, extension_id, proxy)))
            tasks.append(asyncio.create_task(self.check_liveness(token, extension_id, proxy)))
        await asyncio.gather(*tasks)
                # await self.connect_extension(token, extension_id, ip, proxy)
                # await self.check_liveness(token, extension_id, proxy)


    async def main(self):
        self.clear_terminal()
        self.welcome()

        accounts = self.load_accounts()
        if not accounts:
            self.log("No accounts loaded. Please check token.txt.", log_type="ERROR")
            return

        await self.load_proxies()

        # extension_id = input("Enter Extension ID: ").strip()
        # if not extension_id:
        #     self.log("No Extension ID provided.", log_type="ERROR")
        #     return

        self.log(f"Starting bot with {len(accounts)} accounts...")

        while True:
            for account in accounts:
                token = account.get("token")
                if token:
                    await self.process_accounts(token)
                    await asyncio.sleep(5)  # Delay between accounts

            self.log("All accounts processed. Waiting for next cycle...")
            await asyncio.sleep(60 * 60)  # Wait 1 hour before next cycle


if __name__ == "__main__":
    try:
        bot = ExeOSBot()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE} | {Style.RESET_ALL}"
            f"{Fore.RED}[ EXIT ] ExeOS - BOT{Style.RESET_ALL}"
        )
