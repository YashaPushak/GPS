class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    Originally from: https://stackoverflow.com/questions/1165352/calculate-difference-in-keys-contained-in-two-python-dictionaries/1165552#1165552 last accessed 2019-03-20
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        return self.set_current - self.intersect 
    def removed(self):
        return self.set_past - self.intersect 
    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])



def changed(curDict, pastDict):
    #Author: YP
    #Created: 2019-03-20
    #Checks to see if the current dict and past dict are exactly the same.

    diff = DictDiffer(curDict,pastDict)
    
    return len(diff.added()) > 0 or len(diff.removed()) > 0 or len(diff.changed()) > 0
