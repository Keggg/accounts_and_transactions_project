from decimal import Decimal
from uuid import UUID, uuid4
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, HttpRequest

from django.shortcuts import render

from account.account import Account
from database.database import ObjectNotFound
from database.implementations.postgres_db import AccountDatabasePostgres, TransactionDatabasePostgres

connection = "dbname=db port=5432 user=postgres password=19775 host=localhost"
database = AccountDatabasePostgres(connection)
transactions_db = TransactionDatabasePostgres(connection)

def accounts_list(request: HttpRequest) -> HttpResponse:
    accounts = database.get_objects()
    accounts_with_max_balance = database.find_max_balance_per_currency()
    return render(request, "index.html", context={"accounts": accounts, "accounts_with_max_balance": accounts_with_max_balance})

@csrf_exempt
def create_account(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        try:
            account = Account(
                id_ = uuid4(),
                currency = request.POST.get("dropdown_currency", ""),
                balance = Decimal(0),
            )
            try:
                database.get_object(account.id_)
                return HttpResponse(content=f"Error: object already exists, use PUT to update", status=400)
            except ObjectNotFound:
                database.save(account)
                return HttpResponse(content="""<html><script>window.location.replace('/');</script></html>""", status=201)
        except Exception as e:
            return HttpResponse(content=f"Error: {e}", status=400)

@csrf_exempt
def transactions(request: HttpRequest, id_) -> HttpResponse:
    if request.method == "GET":
        account = database.get_object(id_)
        accounts_by_currency = database.get_objects_by_currency(account.id_, account.currency)
        transactions = transactions_db.get_objects_by_account(account.id_)
        if request.GET.get("graph-btn"):
            transactions_db.graph(account, transactions)
        return render(request, "transactions.html", context={"account": account, "accounts_by_currency": accounts_by_currency, "id_": id_, "transactions": transactions})

        

    if request.method == "POST":
        # Перевод денег
        if request.POST.get("transaction_btn"):
            source_account = database.get_object(id_)
            balance_brutto = Decimal(request.POST.get("balance_brutto", ""))
            if balance_brutto <= source_account.balance:
                try:
                    target_account_id = UUID(request.POST.get("dropdown_accounts_for_transaction", ""))
                    target_account = database.get_object(target_account_id)
                    transactions_db.save(source_account, target_account, balance_brutto, database)
                    return HttpResponse(content="""<html><script>window.location.replace('');</script></html>""", status=201)
                except Exception as e:
                    return HttpResponse(content=f"Error: {e}", status=400)
            else:
                return HttpResponse(content="""<html>
                                                    <script>alert("Недостаточно средств на счете");</script><br>
                                                    <script>window.location.replace('');</script>
                                                </html>""")
        # Пополнение баланса
        elif request.POST.get("add_amount_btn"):  
            add_to_account = database.get_object(id_)
            add_amount = Decimal(request.POST.get("add_amount", ""))
            try:
                transactions_db.save(add_to_account, add_to_account, add_amount, database)
                return HttpResponse(content="""<html><script>window.location.replace('');</script></html>""", status=201)
            except Exception as e:
                return HttpResponse(content=f"Error: {e}", status=400)
