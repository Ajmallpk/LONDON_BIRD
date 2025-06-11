from django.shortcuts import render
from django.shortcuts import render,redirect,get_object_or_404
from .models import categories
from django.contrib import messages
from PIL import Image
from django.core.files.base import ContentFile
from io import BytesIO
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import categories
from .forms import CategoryForm
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from .models import categories 
from offer.models import CategoryOffer
from datetime import datetime
from django.utils.timezone import make_aware

def category_list(request):
    category_items = categories.objects.all() 
    search_query = request.GET.get('search', '')
    if search_query:
        category_items = category_items.filter(name__icontains=search_query)

    paginator = Paginator(category_items, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    category_offers = CategoryOffer.objects.filter(category__in=category_items)
    category_offer_dict = {offer.category.id: offer for offer in category_offers}

    if request.method == 'POST':
        if 'add_category_offer' in request.POST:
            category_id = request.POST.get('category_id')
            offer_id = request.POST.get('offer_id', None) 
            discount_percentage = request.POST.get('discount_percentage')
            valid_from = request.POST.get('valid_from')
            valid_until = request.POST.get('valid_until')
            is_active = request.POST.get('is_active') == 'on'

            try:
                discount_percentage = float(discount_percentage)
                if discount_percentage < 0 or discount_percentage > 100:
                    messages.error(request, "Discount percentage must be between 0 and 100.")
                    return redirect('category_list')
                
                
                valid_from_dt = make_aware(datetime.strptime(valid_from, '%Y-%m-%d'))
                valid_until_dt = make_aware(datetime.strptime(valid_until, '%Y-%m-%d'))
                if valid_from_dt > valid_until_dt:
                    messages.error(request, "The 'Valid Until' date must be after the 'Valid From' date.")
                    return redirect('category_list')

                if offer_id:  
                    offer = CategoryOffer.objects.get(id=offer_id)
                    offer.discount_percentage = discount_percentage
                    offer.valid_from = valid_from_dt  
                    offer.valid_until = valid_until_dt 
                    offer.is_active = is_active
                    offer.save()
                    messages.success(request, f"Offer updated successfully for {offer.category.name}.")
                else:  
                    category_instance = categories.objects.get(id=category_id)
                    CategoryOffer.objects.create(
                        category=category_instance,
                        discount_percentage=discount_percentage,
                        valid_from=valid_from_dt,  
                        valid_until=valid_until_dt, 
                        is_active=is_active
                    )
                    messages.success(request, f"Offer added successfully for {category_instance.name}.")
            except ValueError as e:
                messages.error(request, "Invalid input. Please ensure all fields are filled correctly.")
            except (categories.DoesNotExist, CategoryOffer.DoesNotExist):
                messages.error(request, "Category or offer not found.")
            return redirect('category_list')

    return render(request, 'category_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_offer_dict': category_offer_dict,
    })
  
  




@never_cache
@staff_member_required
def add_category(request):
  if request.method=='POST':
    form=CategoryForm(request.POST,request.FILES)
    if form.is_valid():
      category_name = form.cleaned_data['name']
      if categories.objects.filter(name__iexact=category_name).exists():
          messages.error(request, f"A category with the name '{category_name}' already exist")
          return render(request, 'add-category.html', {'form': form})
      category= form.save(commit=False)
      uploaded_image = form.cleaned_data['image']
      image = Image.open(uploaded_image)
      width, height = image.size
      new_size = min(width, height)
      left = (width - new_size) / 2
      top = (height - new_size) / 2
      right = (width + new_size) / 2
      bottom = (height + new_size) / 2
      cropped_image = image.crop((left, top, right, bottom))
      buffer = BytesIO()
      cropped_image.save(buffer, format=image.format)
      category.image.save(uploaded_image.name, ContentFile(buffer.getvalue()), save=False)
      category.save()
      return redirect('category_list')
    else:
      error_list = []
      for field, errors in form.errors.items():
          for error in errors:
              error_list.append(f"{field.capitalize()}: {error}")
      messages.error(request, "Form is not valid: " + " | ".join(error_list))
  else:
    form=CategoryForm()
  return render(request,'add-category.html',{'form': form})







@staff_member_required
@never_cache
def edit_category(request, id):
    category = get_object_or_404(categories, id=id)
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            if 'image' in request.FILES:
                uploaded_image = request.FILES['image']
                try:
                    image = Image.open(uploaded_image)
                    width, height = image.size
                    new_size = min(width, height)
                    left = (width - new_size) / 2
                    top = (height - new_size) / 2
                    right = (width + new_size) / 2
                    bottom = (height + new_size) / 2

                    cropped_image = image.crop((left, top, right, bottom))
                    buffer = BytesIO()
                    cropped_image.save(buffer, format=image.format)
                    category.image.save(uploaded_image.name, ContentFile(buffer.getvalue()), save=False)
                except Exception as e:
                    messages.error(request, f"Image processing failed: {str(e)}")
                    return render(request, 'edit-category.html', {'form': form, 'category': category})
            category.save()
            messages.success(request, "Category updated successfully.")
            return redirect('category_list')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CategoryForm(instance=category)
    return render(request, 'edit-category.html', {'form': form, 'category': category})








@login_required
@never_cache
def unlist_category(request, id):
    category = get_object_or_404(categories, id=id)
    category.is_listed = not category.is_listed  
    category.save()
    status = "listed" if category.is_listed else "unlisted"
    messages.success(request, f"Category {category.name} has been {status}.")
    return redirect('category_list')
