from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required
def profile(request):
    return render(request, 'core/index.html')