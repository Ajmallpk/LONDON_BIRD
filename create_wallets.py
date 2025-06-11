from django.contrib.auth.models import User
from wallet.models import Wallet

def create_wallets_for_existing_users():
    users = User.objects.all()
    for user in users:
        Wallet.objects.get_or_create(user=user)

if __name__ == "__main__":
    create_wallets_for_existing_users()