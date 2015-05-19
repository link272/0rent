import decimal
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

# Everything about Finance
class Balance(object):
    
    def formatting(self, price):
        return price.quantize(Decimal('0.01'), decimal.ROUND_UP)
        
# Everything about Ownership
class Ownership(models.Model):
    
    first_owner = models.ForeignKey(Profil)
    is_public = models.BooleanField(default=True)
    nb_use = models.IntegerFields(default = 0)
    private_group = models.OneToOneField(Group, null=True, blank=True)
    
    # SIGNAUX
    # Création du groupe pour un nouveau produit
    @receiver(post_save, sender=Product)
    def create_group_for_product(sender, instance, created, **kwargs):

        if created:
            # product.check()
            group = Group(name='ppg@{}'.format(instance.id))
            group.save()
            instance.first_owner.groups.add(group)
            instance.private_group = group
    # SIGNAUX
    
    # compte le nombre d'utilisation
    @property
    def nb_use(self):
        return self.use_set.count()
    
    
    
# Everything about Product
class Product(models.Model):
    
    name = models.CharField(max_length=64)
    description = models.TextField(max_length=512, null=True, blank=True)
    post_date = models.DateField(auto_now_add=True)
    update_date = models.DateField(auto_now=True)
    balance = models.OneToOneField(ProductBalance)
    owners = models.OneToOneField(Ownership)


    def __str__(self):
        return self.name


            
# Everything about Product Finance
class ProductBalance(Balance, models.Model):
    
    product = models.OneToOneField(Product)
    initial_cost = models.DecimalField(max_digits=8, decimal_places=2)
    current_cost = models.DecimalField(max_digits=8, decimal_places=2)
    step = models.DecimalField(max_digits=8, decimal_places=2,
                               null=True, blank=True)
                               
    # retourne le prix de la prochaine utilisation
    def updated_cost(self, nb_use):
        if self.step and nb_use * self.step <= self.cost:
            self.current_cost = self.step
        else:
            self.current_cost = self.cost / (1 + nb_use)
            self.current_cost = self.formatting(self.current_cost)
        return current_cost
        
    


# Model Use
class Register(models.Model):
    #  related_name='uses' : uses à la place de use_set
    product = models.ForeignKey(Product)
    user = models.ForeignKey(User)
    date = models.DateField(auto_now_add=True)
    
    # Ajout complet d'une utilisation
    # (remboursement, maj balance utilisateur et création use)
    def add_use_for(self, user):
        with transaction.atomic():
            self.recompute_use_balances()
            profil = user.profil
            profil.balance = profil.balance - self.price
            profil.save()
            # use = Use(product = self, user= request.user)
            # use.save()
            self.use_set.create(user=user)
    
    def recompute_use_balances(self):
        nb_use = self.nb_use
        price = self.price
        step = self.step
        cost = self.cost
        if step:
            # l'utilisation ne suffit pas pour atteindre le cost
            if (nb_use + 1) * step < cost:
                # remboursement du first owner
                profil = self.first_owner.profil
                profil.balance = profil.balance + price
                profil.save()
            # l'utilisation permet d'atteindre le cost
            if nb_use * step < cost <= (nb_use + 1) * step:
                # remboursement du first owner jusqu'a atteindre le cost
                profil = self.first_owner.profil
                profil.balance = profil.balance + (cost - nb_use * step)
                profil.save()
            # l'utilisation précedente a permis d'atteindre le cost
            if (nb_use - 1) * step < cost <= nb_use * step:
                # remboursement des utilisateurs précedents
                # en prenant en compte l'excedent du passage du cost
                for use in self.use_set.all():
                    profil = use.user.profil
                    profil.balance = profil.balance + (step - price)
                    profil.save()
            # le cost a déjà été atteint depuis 2 utilisations ou +
            if cost <= (nb_use - 1) * step:
                # calcul du prix précedent
                previous_price = cost / (nb_use)
                previous_price = previous_price.quantize(Decimal('0.01'),decimal.ROUND_UP)
                # remboursement des utilisateurs précedents
                for use in self.use_set.all():
                    profil = use.user.profil
                    profil.balance = profil.balance + (previous_price - price)
                    profil.save()
        else:
            # le produit a déjà été utilisé
            if nb_use:
                # calcul du prix précedent
                previous_price = cost / (nb_use)
                previous_price = previous_price.quantize(Decimal('0.01'), decimal.ROUND_UP)
                # remboursement des utilisateurs précedents
                for use in self.use_set.all():
                    profil = use.user.profil
                    profil.balance = profil.balance + (previous_price - price)
                    profil.save()
            # le produit n'a jamais été utilisé
            else:
                # remboursement du first owner
                profil = self.first_owner.profil
                profil.balance = profil.balance + price
                profil.save()


# Model Profil
class Profil(User):
        user = models.OneToOneField(User)
        balance = user = models.OneToOneField(ProfilBalance)
        
    #SIGNAUX    
    # Création du profil pour un nouvel utilisateur
    @receiver(post_save, sender=User)
    def create_profil_for_user(sender, instance, created, **kwargs):
        if created:
            Profil.objects.create(user=instance)
    #SIGNAUX
    
    
# Everything about User Finance
class ProfilBalance(Balance, models.Model):

    current = models.DecimalField(max_digits=8, decimal_places=2, default=0)
