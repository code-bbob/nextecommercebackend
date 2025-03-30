from django.db import models
from django.utils import timezone
import uuid
from ckeditor.fields import RichTextField
from django.utils.text import slugify

class Blog(models.Model):
    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id = models.SlugField(primary_key=True, unique=True,blank=True)
    title = models.CharField(max_length=100)
    author = models.CharField(max_length=50)
    content = RichTextField()
    image = models.ImageField(upload_to='blog/images', default='')
    date = models.DateField(default=timezone.now)
    category = models.CharField(max_length=20, default='Technology')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = slugify(self.title)  # Auto-generate the slug from the title

            # Check if a slug already exists and make it unique
            original_id = self.id
            num = 1
            while Blog.objects.filter(id=self.id).exists():  # Check if slug already exists
                self.id = f"{original_id}-{num}"  # Append number to make it unique
                num += 1

        super().save(*args, **kwargs)