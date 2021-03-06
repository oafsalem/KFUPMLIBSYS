from django.db import models
from django.contrib.auth.models import User
from django.db.models import constraints
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
import datetime
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
User._meta.get_field('email').blank = False
from django.core.mail import send_mail
# Create your models here.


class Library_People(models.Model):
    # People_ID????
    People_ID = models.PositiveIntegerField(
        unique=True,
        primary_key=True,
        null=False,
        blank=False,
        # verbose_name=_("")
    )
    user = models.ForeignKey(User,
                             on_delete=models.CASCADE,
                             null=True,
                             blank=True,
                             verbose_name=_("user"))

    @property
    def First_Name(self):
        return self.user.first_name

    @property
    def Last_Name(self):
        return self.user.last_name

    @property
    def date_joined(self):
        return self.user.date_joined


    @property
    def checked_out_books_previously(self):
        member = Member.objects.filter(user=self.user).first()
        member_loans = Book_Loan.objects.filter(borrower= member)
        if len(member_loans)== 0:
            return True
        else:
            return False
    
    Birth_Date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("birth date")
    )
    SEX_CHOICES = (
        ('M', 'Male',),
        ('F', 'Female',),
    )
    sex = models.CharField(
        max_length=1,
        choices=SEX_CHOICES,
        null=False,
        blank=False,
    )

    Department = models.CharField(
        max_length=256,
        blank=True,
        null=True
    )
    Contact_Number = PhoneNumberField(blank=True, null=True)

    @property
    def Email(self):
        return self.user.email

    def __str__(self):
        return "ID: " + str(self.People_ID) + "\tName: " + self.First_Name

    class Meta:
        abstract = True


class Librarian(Library_People):
    pass


class Member(Library_People):
    pass


class Author(Library_People):
    @property
    def number_of_books(self):
        return len(Book.objects.all(Author=self))


class System(Library_People):
    pass


class Subject(models.Model):
    Subject_Id = models.PositiveIntegerField(
        unique=True,
        primary_key=True,
        null=False,
        blank=False,
        # verbose_name=_("")
    )
    subject_name = models.CharField(
        max_length=512,
        blank=False,
        null=False
    )

    def __str__(self):
        return self.subject_name

    class Meta:
        verbose_name = _("subject")
        verbose_name_plural = _("subjects")
        ordering = [
            "subject_name",
        ]


def current_year():
    return datetime.date.today().year


def max_value_current_year(value):
    return MaxValueValidator(current_year())(value)


class Book(models.Model):
    ISBN_code = models.CharField(
        unique=True,
        primary_key=True,
        max_length=64,
        null=False,
        blank=False,
        verbose_name=_("ISBN code")
    )

    book_title = models.CharField(
        max_length=512,
        blank=False,
        null=False,
        verbose_name=_("book title"),
    )
    Lang_CHOICES = (
        ('A', 'Arabic',),
        ('E', 'English',),
    )
    book_language = models.CharField(
        choices=Lang_CHOICES,
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("book language")
    )

    no_of_copies = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("number of copies")
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("subject")
    )

    @property
    def is_available(self):
        return self.no_of_copies > 0
        # Fun Fact: Django ManyToManyField fields are automatically mapped into seperate tabels
    authors = models.ManyToManyField(
        Author,
        blank=True,
        verbose_name=_("authors"),
    )  # RECHECK THIS
    # TRUE

    publication_year = models.PositiveIntegerField(
        default=current_year(),
        validators=[MinValueValidator(1800), max_value_current_year],
        blank=True,
        null=True,
        verbose_name=_("publication year")
    )

    class Meta:
        verbose_name = _("book")
        verbose_name_plural = _("books")

        ordering = [
            "publication_year",
            "book_title",
        ]

    def __str__(self):
        return self.book_title


class Book_Item(models.Model):

    def save(self, *args, **kwargs):
        related_reserves = Book_Reserve.objects.filter(book=self.book)
        emails = []
        for reserve in related_reserves:
            emails.append(reserve.borrower.user.email)
        if len(emails) > 0:
            sent = send_mail(
                subject ='KFUPMLIBSYS Book Reserve is Available',
                message= f'Good News!! Your reserve for Book: {self.book.book_title}, ISBN= {self.book.ISBN_code} is available in our library right now!!',
                from_email='kfupmlibsys@yahoo.com',
                recipient_list=emails)
            print(f"Succesfully Sent {sent}/{str(len(emails))} considring thier reserves!")
        return super().save(*args, **kwargs)


    bar_code = models.CharField(
        max_length=32,
        unique=True,
        primary_key=True,
        verbose_name=_("bar code")
    )
    book = models.ForeignKey(
        Book,  # Check this later
        on_delete=models.CASCADE,
        blank=True,
        null=False,
        verbose_name=_("book"),
    )

    def clean(self):
        if self.book_copy_number > self.book.no_of_copies:
            raise ValidationError(
                _('book copy number must be less than number of copies'))

    book_copy_number = models.PositiveIntegerField(
        verbose_name=_("book copy number"),
    )

    @property
    def loan_status(self):
        loans = Book_Loan.objects.filter(book_item=self)
        for loan in loans:
            if (loan.actual_return_date is None):
                return False
        return True

    class Meta:
        constraints = [
            # This constraint assuers that the borrower, bar_code,
            # and borrowed from are unique in the table.
            models.UniqueConstraint(
                fields=["book", "book_copy_number"],
                name="unique book_copy_number for each book",
            ),
        ]
        verbose_name = _("book item")
        verbose_name_plural = _("book items")

        ordering = [
            "bar_code",
            "book",
        ]

    def __str__(self):
        return self.book.book_title + self.bar_code


class Book_Loan(models.Model):
    borrower = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name=_("borrower")
    )

    book_item = models.ForeignKey(
        Book_Item,
        on_delete=models.CASCADE,
        verbose_name=_("book item")
    )

    borrowed_from = models.DateField(
        verbose_name=_("borrowed from"),
        null=False,
    )
    borrowed_to = models.DateField(
        verbose_name=_("borrowed to"),
        null=False,
    )

    actual_return_date = models.DateField(
        verbose_name=_("actual return date"),
        null=True,
        blank=True,
    )

    issued_by = models.ForeignKey(
        Librarian,
        on_delete=models.CASCADE,
        verbose_name=_("issued by"),
        null=True,
        blank = True
    )

    class Meta:
        constraints = [
            # This constraint assuers that the borrower, bar_code,
            # and borrowed from are unique in the table.
            models.UniqueConstraint(
                fields=["borrower", "book_item", "borrowed_from"],
                name="unique composite Book_Loan primary key",
            ),
        ]
        verbose_name = _("book loan")
        verbose_name_plural = _("book loans")
        ordering = [
            "borrowed_from",
        ]

    def __str__(self):
        return "Book title: " + str(self.book_item.book.book_title) + " Borrower: " + str(self.borrower.First_Name)


class Book_Reserve(models.Model):
    borrower = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        verbose_name=_("borrower")
    )

    book = models.ForeignKey(
        Book,  # Check this later
        on_delete=models.CASCADE,
        blank=True,
        null=False,
        verbose_name=_("book"),
    )

    reserve_date = models.DateField(
        verbose_name=_("reserve date"),
    )

    reserve_status = models.BooleanField(
        verbose_name=_("reserve status")
    )  # Leave as is for now

    def __str__(self):
        return "Book title: " + str(self.book.book_title) + " Reserver: " + str(self.borrower.First_Name)

    class Meta:
        constraints = [
            # This constraint assuers that the borrower, bar_code,
            # and borrowed from are unique in the table.
            models.UniqueConstraint(
                fields=["borrower", "book"],
                name="unique composite Book_Reserve primary key",
            ),
        ]
        verbose_name = _("book reserve")
        verbose_name_plural = _("book reserves")
        ordering = [
            "reserve_date",
        ]


class Book_Shelf(models.Model):
    Shelf_ID = models.PositiveIntegerField(
        unique=True,
        primary_key=True,
        null=False,
        blank=False,
        verbose_name=_("ISBN code")
    )
    Shelf_No = models.CharField(
        max_length=4,
        # verbose_name=_("")
    )
    Floor_No = models.PositiveIntegerField(
        # verbose_name=_("")
    )
