import asyncio
from aiohttp import ClientSession,TCPConnector
from json import JSONEncoder, loads

import requests

class Payment:
    """Класс сгенерированной оплаты.
    """

    def __init__(self, payment_id : str, default_params : dict, amount : int = None):
        self.id = payment_id
        self.default_params = default_params
        self.url = f"https://pay.crystalpay.io/v2.php?i={self.id}"
        self.api_url = "https://api.crystalpay.io/v2/invoice/info/"
        self.paymethod = None
        if amount:
            self.amount = amount
        else:
            self.__get_amount()

    def if_paid(self) -> bool:
        params = self.default_params
        params['id'] = self.id
        params = JSONEncoder().encode(params)
        header = {
            "Content-Type": "application/json;charset=UTF-8",
        }
        header['Content-Length'] = str(len(params))

        resp = requests.post(self.api_url, data=params,headers=header)
        if resp.status_code == 403:
            raise AuthError("Ошибка авторизации")
        data = resp.json()
            
        if data['error']:
            raise CheckPaymentErr(f"Ошибка проверки платежа: {data['errors']}")
        if data['state'] == "payed":
            return True
        else:
            return False
    
    def __get_amount(self) -> None:
        params = self.default_params
        params['id'] = self.id
        params = JSONEncoder().encode(params)
        header = {
            "Content-Type": "application/json;charset=UTF-8",
        }
        header['Content-Length'] = str(len(params))

        resp = requests.post(self.api_url, data=params,headers=header)
        if resp.status_code == 403:
            raise AuthError("Ошибка авторизации")
        data = resp.json()

        if data['error']:
            raise CheckPaymentErr(f"Ошибка проверки платежа: {data['errors']}")
        self.amount = data['amount']

class CrystalPay:
    def __init__(self, api_key,secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = ClientSession(connector=TCPConnector(verify_ssl=False))
        self.api_url = "https://api.crystalpay.io/v2/invoice/create/"
        self.def_params = {
            "auth_login": self.api_key,
            "auth_secret" : self.secret_key
        }



    async def create_invoice(self,
        amount : int,
        currency : str = None,
        lifetime : int = None,
        redirect : str = None,
        callback : str = None,
        extra : str = None,
        payment_system : str = None,
        ) -> Payment:
        """Метод генерации ссылки для оплаты 
        amount - сумма на оплату(целочисл.)
        currency - 	Валюта суммы (конвертируется в рубли) (USD, BTC, ETH, LTC…) (необязательно)
        liftetime - Время жизни счёта для оплаты, в минутах (необязательно)
        redirect - Ссылка для перенаправления после оплаты (необязательно)
        callback - Ссылка на скрипт, на который будет отправлен запрос, после успешного зачисления средств на счёт кассы (необязательно)
        extra - Любые текстовые данные, пометка/комментарий. Будет передано в callback или при проверке статуса платежа (необязательно)
        payment_system - Если нужно принудительно указать платежную систему (необязательно).
        """

        temp_params = self.def_params
        temp_params['amount'] = amount
        temp_params['type'] = "purchase"
        temp_params["lifetime"] = 15
        # Google Chrome
        header = {
            "Content-Type": "application/json;charset=UTF-8",
        }
        if currency:
            temp_params['currency'] = currency
        if lifetime:
            temp_params['liftetime'] = lifetime
        if redirect:
            temp_params['redirect'] = redirect
        if callback:
            temp_params['callback'] = callback
        if extra:
            temp_params['extra'] = extra
        if payment_system:
            temp_params['m'] = payment_system

        encoder = JSONEncoder()
        temp_params = encoder.encode(temp_params)
        header['Content-Length'] = str(len(temp_params))

        async with self.session.post(self.api_url, data=temp_params, headers=header) as resp:
            if resp.status == 403:
                raise AuthError("Ошибка авторизации")
            text = await resp.text()
        data = loads(text)
        await self.session.connector.close()
        await self.session.close()
        if data['error']:
            raise CreatePaymentError(f"Ошибка создания платежа: {data['errors']}")

        return Payment(data['id'], self.def_params, amount)
    

    def construct_payment_by_id(self, paymnet_id) -> Payment:
        return Payment(paymnet_id, self.def_params)


class AuthError(Exception):
    pass

class CreatePaymentError(Exception):
    pass

class CheckPaymentErr(Exception):
    pass