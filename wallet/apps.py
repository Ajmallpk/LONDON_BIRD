from django.apps import AppConfig


class WalletConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallet'



    # --- UPDATED CODE ---
    def ready(self):
        import wallet.signals
    # --- END UPDATED CODE ---