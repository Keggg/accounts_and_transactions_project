from typing import List, Optional
from uuid import UUID, uuid4
import psycopg2
import pandas as pd
import numpy as np
from pandas import Series
from account.account import Account
from database.database import AccountDatabase, TransactionDatabase
from database.database import ObjectNotFound
from transaction.transaction import Transaction

from matplotlib import pyplot as plt


class AccountDatabasePostgres(AccountDatabase):
    def __init__(self, connection: str,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = psycopg2.connect(connection)
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id varchar primary key ,
            currency varchar ,
            balance decimal 
        );
        """)
        self.conn.commit()


    def close_connection(self):
        self.conn.close()

    def _save(self, account: Account) -> None:
        if account.id_ is None:
            account.id_ = uuid4()

        cur = self.conn.cursor()
        cur.execute("""
                UPDATE accounts SET currency = %s, balance = %s WHERE id = %s;
        """, (account.currency, account.balance, str(account.id_)))
        rows_count = cur.rowcount
        self.conn.commit()

        print("ROWS COUNT", rows_count)
        if rows_count == 0:
            cur = self.conn.cursor()
            cur.execute("""
                    INSERT INTO accounts (id, currency, balance) VALUES (%s, %s, %s);
                    """, (str(account.id_), account.currency, account.balance))
            self.conn.commit()

    def clear_all(self) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM accounts;")
        self.conn.commit()

    def get_objects(self) -> List[Account]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM accounts ORDER BY currency, balance DESC;")
        data = cur.fetchall()
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return [self.pandas_row_to_account(row) for index, row in df.iterrows()]

    def get_objects_by_currency(self, id_: UUID, currency) -> List[Account]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE id != %s AND currency = %s;", (str(id_), currency,))
        data = cur.fetchall()
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return [self.pandas_row_to_account(row) for index, row in df.iterrows()]

    def pandas_row_to_account(self, row: Series) -> Account:
        return Account(
            id_=UUID(row["id"]),
            currency=row["currency"],
            balance=row["balance"],
        )

    def get_object(self, id_: UUID) -> Optional[Account]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE id = %s;", (str(id_),))
        print("Trying to find", str(id_))
        data = cur.fetchall()
        if len(data) == 0:
            raise ObjectNotFound("Oracle: Object not found")
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return self.pandas_row_to_account(row=df.iloc[0])

    def delete(self, id_: UUID) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id = %s;", (str(id_),))
        self.conn.commit()

    def find_max_balance_per_currency(self):
        cur = self.conn.cursor()
        cur.execute("""
        WITH table1 (currency, balance)
            AS (SELECT currency, MAX(balance) as balance
                FROM accounts GROUP BY currency)
        select id, ac.currency, ac.balance from accounts ac
            JOIN table1 t1
                ON ac.currency = t1.currency
                AND ac.balance = t1.balance;
        """)
        data = cur.fetchall()
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return [self.pandas_row_to_account(row) for index, row in df.iterrows()]


class TransactionDatabasePostgres(TransactionDatabase):
    def __init__(self, connection: str,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conn = psycopg2.connect(connection)
        cur = self.conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id varchar primary key ,
            source_account varchar ,
            target_account varchar ,
            balance_brutto decimal ,
            balance_netto decimal ,
            currency varchar ,
            status varchar 
        );
        """)
        self.conn.commit()

    def _save(self, source_account: Account, target_account: Account, balance_brutto, db) -> None:
        transaction_id = uuid4()
        balance_netto = balance_brutto
        transaction_currency = source_account.currency
        status = "Failed"
        # Транзакция перевода
        if source_account != target_account:
            source_account.balance = source_account.balance - balance_brutto
            target_account.balance = target_account.balance + balance_netto
            db.save(source_account)
        # Транзакция пополнения
        elif source_account == target_account:
            target_account.balance = target_account.balance + balance_brutto
        db.save(target_account)
        status = "Success"
        cur = self.conn.cursor()
        cur.execute("""
                INSERT INTO transactions (id, source_account, target_account, balance_brutto, balance_netto, currency, status) VALUES (%s, %s, %s, %s, %s, %s, %s);
                """, (str(transaction_id), str(source_account.id_), str(target_account.id_), balance_brutto, balance_netto, transaction_currency, status))
        self.conn.commit()
        

    def clear_all(self) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM transactions;")
        self.conn.commit()

    def get_objects(self) -> List[Transaction]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM transactions;")
        data = cur.fetchall()
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return [self.pandas_row_to_transaction(row) for index, row in df.iterrows()]

    def get_objects_by_account(self, id_: UUID) -> List[Transaction]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE source_account = %s OR target_account = %s;", (str(id_), str(id_),))
        data = cur.fetchall()
        data = reversed(data)
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return [self.pandas_row_to_transaction(row) for index, row in df.iterrows()]

    def pandas_row_to_transaction(self, row: Series) -> Transaction:
        return Transaction(
            id_=UUID(row["id"]),
            source_account=UUID(row["source_account"]),
            target_account=UUID(row["target_account"]),
            balance_brutto=row["balance_brutto"],
            balance_netto=row["balance_netto"],
            currency=row["currency"],
            status=row["status"],
        )

    def get_object(self, id_: UUID) -> Transaction:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE id = %s;", (str(id_),))
        print("Trying to find", str(id_))
        data = cur.fetchall()
        if len(data) == 0:
            raise ObjectNotFound("Oracle: Object not found")
        cols = [x[0] for x in cur.description]
        df = pd.DataFrame(data, columns=cols)
        return self.pandas_row_to_transaction(row=df.iloc[0])

    def delete(self, id_: UUID) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id = %s;", (str(id_),))
        self.conn.commit()

    def graph(self, account: Account, transactions) -> None:
        x_amount_of_transactions = [0]
        y_balance = []
        count_transactions = 0
        balance = account.balance
        y_balance.append(balance)
        for transaction in transactions:
            count_transactions += 1
            if transaction.source_account == account.id_ and transaction.target_account == account.id_:
                balance = balance - transaction.balance_netto
                y_balance.append(balance)
            elif transaction.source_account == account.id_:
                balance = balance + transaction.balance_brutto
                y_balance.append(balance)
            elif transaction.target_account == account.id_:
                balance = balance - transaction.balance_netto
                y_balance.append(balance)
            x_amount_of_transactions.append(count_transactions)

        y_balance = list(reversed(y_balance))
        plt.style.use('ggplot')
        plt.plot(x_amount_of_transactions, y_balance, marker="o", color='g', label='Balance in ({0}) by a transaction'.format(account.currency))
        plt.xticks(np.arange(min(x_amount_of_transactions), max(x_amount_of_transactions)+1, 1.0))
        plt.xlabel('Количество транзакций')
        plt.ylabel('Баланс на счете')
        plt.legend()
        plt.tight_layout()
        plt.show()
    