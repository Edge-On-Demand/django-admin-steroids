from django.db import models


class Person(models.Model):

    name = models.CharField(max_length=100, blank=False, null=False, unique=True)

    associates = models.ManyToManyField('self', blank=True)


class Contact(models.Model):

    person = models.ForeignKey(Person, on_delete=models.CASCADE)

    email = models.EmailField(max_length=100, blank=False, null=False)

    class Meta:
        unique_together = (('person', 'email'),)
