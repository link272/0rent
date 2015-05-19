import decimal
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

"""
                    User                Product
                    Profil              -
Balance     =>      ProfilBalance       ProductBalance
                        Register <=> Ownership
"""

# Everything about Finance
class Balance(object):
    
    def formatting(self, price):
        return price.quantize(Decimal('0.01'), decimal.ROUND_UP)
        
# Everything about Ownership
class Ownership(models.Model):
    
    first_owner = models.ForeignKey(Profil)
    is_public = models.BooleanField(default=True)
    nb_use = models.IntegerFields(default = 0)
    product_group = models.OneToOneField(Group, null=True, blank=True)
    
    def update_nb_use(self):
    	group = self.product_group.objects.all()
		self.nb_use = group.count()
		self.save()
		return self
	
	# SIGNAUX
    @receiver(post_save, sender=Product)
    def create_group_for_product(self, sender, created, **kwargs):
        if created:
            group = Group(name='ppg@{}'.format(instance.id))
            group.save()
            self.first_owner.groups.add(group) #????????
            self.product_group = group
            self.save()
    # SIGNAUX
    
    
    
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
                               
    # recalcul le prix de la prochaine utilisation
    def update_current_cost(self, nb_use):
        if self.step and nb_use * self.step <= self.cost:
            self.current_cost = self.step
        else:
            self.current_cost = self.cost / (1 + nb_use)
            self.current_cost = self.formatting(self.current_cost)
        self.save()
        
    


# Model Use
class Register(models.Model):
    
    product = models.ForeignKey(Product)
    user = models.ForeignKey(User)
    date = models.DateField(auto_now_add=True)
    
    def update_user_balance(self):
        balance.current = balance.current - self.product.current_cost
        self.profil.save()
    
    # Ajout complet d'une utilisation
    # (remboursement, maj balance utilisateur et création use)
    def use_product_for(self, user):
        with transaction.atomic(): #??????????
            self.recompute_use_balances()
            self.use_set.create(user=user)
    
    def recompute_group_users_balances(self):
        nb_use = self.product.owners.nb_use
        price = self.product.current_cost
        step = self.product.step
        cost = self.product.initial_cost
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
