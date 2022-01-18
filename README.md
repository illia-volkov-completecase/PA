# Billing app

### Starting application

docker-compose up -d

Note: dev compose file doesn't start server


### Manage scripts

1. `./manage/py test` or `./manage/py t` - run tests
2. `./manage/py alembic` or `./manage/py a` - proxy command to alembic, for instance `./manage/py a upgrade head`
3. `./manage/py load_fixtures` or `./manage/py f` - load fixtures
4. `./manage/py runserver` or `./manage/py r` - start app server
5. `./manage/py shell` or `./manage/py s` - start app shell
6. `./manage/py dbshell` or `./manage/py db` - start dbshell
7. `./manage/py add_user staff` or `./manage/py add_user merchant` - create staff/merchant account
8. `./manage/sh` - opens bash inside container

### Minimal working example
1. Run migrations
`./manage/py a upgrade head`
2. Create merchant account
`./manage/py add_user staff`
3. Run server
`./manage/py r`
4. Open API docs at http://localhost:8000/docs
5. Open web UI (different for staff & merchant, uses API) http://localhost:8000/
6. Login under merchant account, add wallet, create invoice
7. Pay invoice with API
Get payment info
```
http -pb http://localhost:8000/pay/7ef59780-46cb-469f-96b3-d62fba7b64f3
{
    "amount": 100.0,
    "currency_id": 1,
    "paid": 0,
    "unpaid": 100.0,
    "wallet_id": 1
}
```
Get conversion rates **to** currency
```
http -pb http://localhost:8000/rates/1
{
    "rates": {
        "1": 1,
        "2": 0.03571428571428571,
        "3": 0.03132832080200501,
        "4": 0.02600250626566416
    }
}
```
Create transaction
```
http -pb POST http://localhost:8000/pay/7ef59780-46cb-469f-96b3-d62fba7b64f3 currency_id=2 amount=1.00
{
    "attempt": "http://localhost:8000/attempt/387c320c-dd03-4bce-99e1-3f68280b81ad",
    "token": "387c320c-dd03-4bce-99e1-3f68280b81ad"
}
```
Get payment systems for transaction
```
http -pb http://localhost:8000/attempt/387c320c-dd03-4bce-99e1-3f68280b81ad
[
    {
        "id": 1,
        "name": "visa",
        "type": "visa"
    }
]
```
Create payment attempt
```
http -pb POST http://localhost:8000/attempt/387c320c-dd03-4bce-99e1-3f68280b81ad payment_system_id=1
{
    "url": "payment url, use `./manage.py emulate_response 1` to emulate payment response"
}
```
Emulate postback
```
./manage/py emulate_response 1
choose status [s]uccess/[f]ail/[e]rror: s
sending b'gAAAAABh5yHBK0xxeb_xN-X96zdmwQsDbvpzRI7nBxmlis5kCQMLEzZ1DKyLLNg6M-kAtiRjpmwuw-aNZgr4CY0Snb5eWxTrT1ApyGHU0F4ooEiUwAbJ59pKSYDNaeyF1M1gc8Ul7Bdk'
to http://localhost:8000/visa/1/
status code: 200
body: b'{}'
```
Check transaction
```
http -pb http://localhost:8000/pay/7ef59780-46cb-469f-96b3-d62fba7b64f3
{
    "amount": 100.0,
    "currency_id": 1,
    "paid": 28.0,
    "unpaid": 72.0,
    "wallet_id": 1
}
```
You can also login to webui under staff account and refund transaction (change status to refunded)
Check transaction again
```
http -pb http://localhost:8000/pay/7ef59780-46cb-469f-96b3-d62fba7b64f3
{
    "amount": 100.0,
    "currency_id": 1,
    "paid": 0,
    "unpaid": 100.0,
    "wallet_id": 1
}
```