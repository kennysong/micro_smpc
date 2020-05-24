from random import choice, randrange

Q = 18446744073709551557

class VirtualMachine():
    def __init__(self, name):
        self.name = name
        self.objects = []
    
    def __repr__(self):
        string = f'Machine(\'{self.name}\') has:\n'
        for obj in self.objects: string += f'    {obj}\n'
        return string

class PrivateScalar():
    def __init__(self, value, owner):
        self.value = value
        self.owner = owner
        owner.objects.append(self)

    def share(self, machines):
        # Make sure we're sharing across unique machines
        assert self.owner not in machines
        assert len(machines) == len(set(machines))
        
        # Generate the value of each share using additive secret sharing
        values = [randrange(Q) for _ in machines]
        values.append((self.value - sum(values)) % Q)
        
        # Give shares to each machine
        shares = [Share(value, machine) for value, machine in
                  zip(values, machines + [self.owner])]
        
        # Return a SharedScalar that tracks all of these shares
        return SharedScalar(shares)
    
    def __repr__(self):
        return f'PrivateScalar({self.value}, \'{self.owner.name}\')'
            
class Share():
    def __init__(self, value, owner):
        self.value = value
        self.owner = owner
        owner.objects.append(self)
    
    def __repr__(self):
        return f'Share({self.value}, \'{self.owner.name}\')'
    
class SharedScalar():
    def __init__(self, shares):
        self.shares = shares
        self.owners = {share.owner for share in shares}
        self.share_of = {share.owner: share for share in shares}
        
    def reconstruct(self, owner):
        assert owner in self.owners        
        values = [share.value for share in self.shares]
        value = sum(values) % Q
        return PrivateScalar(value, owner)
    
    # Called by: self + other
    def __add__(self, other):
        # Addition of a SharedScalar and a public integer known to all machines
        if isinstance(other, int):
            new_share = Share(self.shares[0].value + other, self.shares[0].owner)
            return SharedScalar([new_share] + self.shares[1:])
        
        # Addition of two SharedScalars
        elif isinstance(other, SharedScalar):
            assert self.owners == other.owners
            sum_shares = []
            for owner in self.owners:
                self_share, other_share = self.share_of[owner], other.share_of[owner] 
                sum_share = Share((self_share.value + other_share.value) % Q, owner)
                sum_shares.append(sum_share)
            return SharedScalar(sum_shares)
        
    # Called by: other + self (when other is not a SharedScalar)
    def __radd__(self, other):
        return self.__add__(other)
    
    # Called by: self - other
    def __sub__(self, other):
        return self.__add__(-1*other)
    
    # Called by: other - self (when other is not a SharedScalar)
    def __rsub__(self, other):
        return (-1*self).__add__(other)
    
    # Called by: self * other
    def __mul__(self, other):
        # Multiplication of a SharedScalar and a public integer known to all machines
        if isinstance(other, int):
            prod_shares = [Share(share.value * other, share.owner) 
                           for share in self.shares]
            return SharedScalar(prod_shares)
            
        # Multiplication of two SharedScalars
        elif isinstance(other, SharedScalar):
            assert self.owners == other.owners

            # Generate a random multiplication triple
            a, b = randrange(Q), randrange(Q)
            c = (a * b) % Q

            # Share the triple
            rand_owner = choice(self.shares).owner
            other_owners = list(self.owners - {rand_owner})
            shared_a = PrivateScalar(a, rand_owner).share(other_owners)
            shared_b = PrivateScalar(b, rand_owner).share(other_owners)
            shared_c = PrivateScalar(c, rand_owner).share(other_owners)

            # Compute (shared) self - a, other - b
            shared_self_m_a = self - shared_a
            shared_other_m_b = other - shared_b

            # Reconstruct (public) self - a, other - b
            self_m_a = shared_self_m_a.reconstruct(rand_owner).value
            other_m_b = shared_other_m_b.reconstruct(rand_owner).value
            
            # Magic! Compute each machine's share of the product
            shared_prod = shared_c + (self_m_a * shared_b) + (other_m_b * shared_a) + (self_m_a * other_m_b)
            return shared_prod
            
    # Called by: other * self (when other is not a SharedScalar)  
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __repr__(self):
        string = 'SharedScalar(\n'
        for share in self.shares:
            string += f'    {share}\n'
        return string + ')'