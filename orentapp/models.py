import decimal
from decimal import Decimal
from django.db import models, transaction
from django.contrib.auth.models import User, Group
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


# Everything about Finance
class MixinBalance(models.Model):

	class Meta:
		abstract = True
		
	current = models.DecimalField(max_digits=8, decimal_places=2, default=0)
	update_date = models.DateField(auto_now=True)
	
	def __str__(self):
		return self.current
    
    def formatting(self, price):
        return price.quantize(Decimal('0.01'), decimal.ROUND_UP)
        
    def credit(self, credit = 0.0):
    	self.current = self.formatting(self.current + credit)
    	self.save()
    	
    def debit(self, debit = 0.0):
    	self.current = self.formatting(self.current - debit)
    	self.save()


        
# Model Profil
class Profil(User):

    balance = models.OneToOneField(ProfilBalance)

	@classmethod
    def build(cls, dic):
        balance_user = ProfilBalance.build(dic)
        profil = cls.create(user = dic[user], balance = balance_user)
    	return profil
    
# Everything about User Finance
class ProfilBalance(MixinBalance):

	@classmethod
	def build(cls, dic):
		balance = cls.create()
		return balance
    
# Everything about Product
class Product(models.Model):
    
    name = models.CharField(max_length=64)
    description = models.TextField(max_length=512, null=True, blank=True)
    post_date = models.DateField(auto_now_add=True)
    balance = models.OneToOneField(ProductBalance)
    ownership = models.OneToOneField(ProductOwnership)
    
    @classmethod
    def build(cls, dic):
    	balance_product = ProductBalance.build(dic)
    	ownership_product = ProductOwership.build(dic)
    	product = cls.create(name = dic["name"],
    					description = dic["description"],
    					balance = balance_product,
    					owners = ownership_product)
    	return product

    def __str__(self):
        return self.name
            
# Everything about Product Finance
class ProductBalance(MixinBalance):
    
    initial_cost = models.DecimalField(max_digits=8, decimal_places=2)
    step = models.DecimalField(max_digits=8, decimal_places=2,
                               null=True, blank=True)
    
    @classmethod                           
   	def build(self, dic):
		balance = cls.create(dic[initial_cost], dic[step])
		return balance
                               
    # recalcul le prix de la prochaine utilisation
    def update_current_cost(self, nb_use):
        if self.step and nb_use * self.step <= self.cost:
            self.current_cost = self.step
        else:
            self.current_cost = self.cost / (1 + nb_use)
            self.current_cost = self.formatting(self.current_cost)
        self.save()
        
# Everything about Ownership
class ProductOwnership(models.Model):
    
    first_owner = models.ForeignKey(Profil)
    is_public = models.BooleanField(default=True)
    nb_use = models.IntegerFields(default = 0)
    private_group = models.ForeignKey(PrivateGroup, null=True, blank=True)
    product_group = models.OneToOneField(Group, null=True, blank=True)
    update_date = models.DateField(auto_now=True)
    
    @classmethod
    def build(cls, dic):
    	product_group_owners = ProductGroup.build(dic)
    	ownership = cls.create(first_owner = dic["first_owner"],
    							is_public = dic["is_public"],
    							product_group = product_group_owners)
    	ownership.update_nb_use()
    	if ownership.is_public = False:
    		ownership.add_private_group(dic)
    	return product
    		
    def add_private_group(self, dic):
    	self.private_group = PrivateGroup.build(self, dic)
    	self.save()
    	return self
    
    def update_nb_use(self):
    	if self.nb_use == 0:
    		group = self.product_group.objects.all()
		self.nb_use = group.count()
	else:
		self.nb_use += 1
	self.save()
	
	# SIGNAUX
    @receiver(post_save, sender=Product)
    def create_product_group(self, sender, created, **kwargs):
        if created:
            group = Group(name='ppg@{}'.format(instance.id))
            group.save()
            self.first_owner.groups.add(group) #????????
            self.product_group = group
            self.save()
    # SIGNAUX
    
class GroupMixin(models.Model):
	
	class Meta:
		abstract = True
	
	def register_group(self, *args):
		for user in args:
			user.group.add(self)
		return self
    
class PrivateGroup(Group, GroupMixin):
	
	admin = models.ForeignKey(Profil)
	
	@classmethod
	def build(cls, dic):
		group = cls.create(group_name = dic["group_name"], admin = dic ["admin"])
		group.register_group(*dic["private_group_members"])
		return group
		
		
class ProductGroup(Group, GroupMixin):
	
	@classmethod
	def build(cls, dic):
		group = cls.create()
		group.register_group(*dic["product_group_members"])
		return group
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
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

