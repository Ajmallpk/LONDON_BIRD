from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .models import Wallet, WalletTransaction
from django.contrib import messages
import decimal




@login_required
def wallet_page(request):

    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet).order_by('-created_at')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'wallet_page.html', context)




@login_required
def add_money(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        
        if not amount or amount.strip() == '':
            messages.error(request, "Please enter a valid amount.")
            return redirect('wallet_page')
        try:
           
            amount = decimal.Decimal(amount)
            if amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return redirect('wallet_page')
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='CREDIT',
                amount=amount,
                description='Added money to wallet'
            )
            wallet.balance += amount
            wallet.save()
            messages.success(request, f"Successfully added ₹{amount:.2f} to your wallet.")
            return redirect('wallet_page')
        except (ValueError, decimal.InvalidOperation):
            messages.error(request, "Invalid amount entered.")
            return redirect('wallet_page')
   
    return render(request, 'add_money.html', {'wallet': wallet})

