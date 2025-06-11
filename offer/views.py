from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from .models import ProductOffer, CategoryOffer
from products.models import product
from categories.models import categories

def is_admin(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_admin)
def offer_management(request):
    product_offers = ProductOffer.objects.all()
    category_offers = CategoryOffer.objects.all()
    
    context = {
        'product_offers': product_offers,
        'category_offers': category_offers,
    }
    return render(request, 'offer_management.html', context)




@user_passes_test(is_admin)
def add_product_offer(request):
    if request.method == 'POST':
        product_id = request.POST.get('product')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')
        is_active = request.POST.get('is_active') == 'on'

        try:
            selected_product = product.objects.get(id=product_id)
            ProductOffer.objects.create(
                product=selected_product,
                discount_percentage=discount_percentage,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=is_active
            )
            messages.success(request, "Product offer added successfully!")
            return redirect('offer_management')
        except product.DoesNotExist:
            messages.error(request, "Selected product does not exist.")
        except Exception as e:
            messages.error(request, f"Error adding product offer: {str(e)}")

    products = product.objects.all()
    context = {'products': products}
    return render(request, 'add_product_offer.html', context)





@user_passes_test(is_admin)
def edit_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    if request.method == 'POST':
        product_id = request.POST.get('product')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')
        is_active = request.POST.get('is_active') == 'on'

        try:
            selected_product = product.objects.get(id=product_id)
            offer.product = selected_product
            offer.discount_percentage = discount_percentage
            offer.valid_from = valid_from
            offer.valid_until = valid_until
            offer.is_active = is_active
            offer.save()
            messages.success(request, "Product offer updated successfully!")
            return redirect('offer_management')
        except product.DoesNotExist:
            messages.error(request, "Selected product does not exist.")
        except Exception as e:
            messages.error(request, f"Error updating product offer: {str(e)}")

    products = product.objects.all()
    context = {'offer': offer, 'products': products}
    return render(request, 'edit_product_offer.html', context)

@user_passes_test(is_admin)
def delete_product_offer(request, offer_id):
    offer = get_object_or_404(ProductOffer, id=offer_id)
    offer.delete()
    messages.success(request, "Product offer deleted successfully!")
    return redirect('product_list')




@user_passes_test(is_admin)
def add_category_offer(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')
        is_active = request.POST.get('is_active') == 'on'

        try:
            category = categories.objects.get(id=category_id)
            CategoryOffer.objects.create(
                category=category,
                discount_percentage=discount_percentage,
                valid_from=valid_from,
                valid_until=valid_until,
                is_active=is_active
            )
            messages.success(request, "Category offer added successfully!")
            return redirect('offer_management')
        except categories.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
        except Exception as e:
            messages.error(request, f"Error adding category offer: {str(e)}")

    all_categories = categories.objects.all()
    context = {'categories': all_categories}
    return render(request, 'add_category_offer.html', context)





@user_passes_test(is_admin)
def edit_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    if request.method == 'POST':
        category_id = request.POST.get('category')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_until = request.POST.get('valid_until')
        is_active = request.POST.get('is_active') == 'on'

        try:
            category = categories.objects.get(id=category_id)
            offer.category = category
            offer.discount_percentage = discount_percentage
            offer.valid_from = valid_from
            offer.valid_until = valid_until
            offer.is_active = is_active
            offer.save()
            messages.success(request, "Category offer updated successfully!")
            return redirect('offer_management')
        except categories.DoesNotExist:
            messages.error(request, "Selected category does not exist.")
        except Exception as e:
            messages.error(request, f"Error updating category offer: {str(e)}")

    all_categories = categories.objects.all()
    context = {'offer': offer, 'categories': all_categories}
    return render(request, 'edit_category_offer.html', context)

@user_passes_test(is_admin)
def delete_category_offer(request, offer_id):
    offer = get_object_or_404(CategoryOffer, id=offer_id)
    offer.delete()
    messages.success(request, "Category offer deleted successfully!")
    return redirect('category_list')