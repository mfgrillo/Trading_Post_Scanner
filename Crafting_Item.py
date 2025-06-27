# %%
import requests
import pandas as pd
import webbrowser

# Hard-coded recipe IDs for specific item IDs, bug reported here: https://github.com/gw2-api/issues/issues/112
HARDCODED_RECIPES = {
    97339: 13584,  # Core tier 1
    97041: 13542,  # Core tier 2
    97284: 13550,  # Core tier 3
    96628: 13821,  # Core tier 4
    95864: 13658,  # Core tier 5
    96467: 13723,  # Core tier 6
    97020: 13751,  # Core tier 7
    96299: 13780,  # Core tier 8
    96070: 13841,  # Core tier 9
    96613: 13628,  # Core tier 10

    100941: 14018, # Rare Rift Motivation
    100364: 14029, # Masterwork Rift Motivation
    100060: 13957, # Fine Rift Motivation

    97487: 13839  # Piece of Dragon Jade
}



debug_mode = False

GLOBAL_ITEM_LIBRARY = {} # Global item library to avoid redundant API calls, key is item ID, value is CraftingItem object. Item is stored here after it is fetched from the API.
# %%
class CraftingItem:

    def __init__(self, item_id):
        self.item_id = item_id # Item ID from the API
        self.item_type = None  # Item type from the API, e.g. "Item", "Currency", etc.
        self.item_name = None  # Item name from the API
        self.base_ingredients = None  # Children items and their quantities
        self.raw_ingredients = None  # Raw ingredients for this item
        self.raw_ingredients_dataframe = None  # self.raw_ingredients as a DataFrame
        self.recipe_id = None  # Recipe ID for this item
        self.recipe_data = None  # Full recipe data from the API
        self.price = None  # Current buy price from the API
        self.price_instant = None  # Current instant buy price from the API
        self.crafting_cost = 0  # Total crafting cost of this item
        self.volume = None  # Volume of this item
        self.profit_margin = None  # Profit margin of this item
        self.profit_margin_insta = None # Profit margin of this item using instant sell price
        self.metrics_dict = {}  # Analysis metrics for this item

    @staticmethod
    def api_querier(url, params=None):
        """Static method to query the Guild Wars 2 API."""
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        elif response.json() == {"text": "no such id"}:
            return False
        else:
            raise Exception(f"API request failed with status code {response.status_code}: {response.text}")
        
    def get_everything(self):
        """Get all data for this item, populating missing fields as needed."""
        if self.item_name is None:
            self.get_item_name()

        if self.recipe_id is None:
            self.get_recipe_id()

        if self.recipe_data is None:
            self.get_recipe_data()

        if self.base_ingredients is None:
            self.fetch_ingredients()

        if self.raw_ingredients is None:
            self.get_raw_ingredients()

        if self.price is None:
            self.get_item_price()

        if self.crafting_cost == 0:
            self.calculate_crafting_cost()

        if self.profit_margin is None:
            self.calculate_profit_margin()

    def get_everything_child(self):
        """Get child data, necessary for recursion."""

        if self.item_type == "Currency":
            # For currencies, we only need the item name and price (for Research Notes)
            if self.item_name is None:
                self.get_item_name()
            if self.price is None:
                self.get_item_price()

        else:        
            if self.item_name is None:
                self.get_item_name()

            if self.recipe_id is None:
                self.get_recipe_id()

            if self.recipe_data is None:
                self.get_recipe_data()

            if self.base_ingredients is None:
                self.fetch_ingredients()

            if len(self.base_ingredients) == 0 and self.price is None:
                self.get_item_price()
    
        
    def get_item_name(self):
        """Fetch the name of this item from the API."""
        if self.item_name is None:
            # ID 61 is for research notes, which are from a different set of ids since they are a currency, cannot be queried from the API so hardcoding it
            if self.item_type == "Currency":
                url = f"https://api.guildwars2.com/v2/currencies?ids={self.item_id}"
                response = self.api_querier(url)[0]
                # self.item_name = "Research Note"
                # return self.item_name
            else:
                url = f"https://api.guildwars2.com/v2/items/{self.item_id}?lang=en"   
                response = self.api_querier(url)

            if response:
                self.item_name = response["name"] 
                if debug_mode:
                    print(f"Item name for {self.item_id} is {self.item_name}")
                return self.item_name
            else:
                return False


        return self.item_name

    def get_recipe_id(self):
        """Fetch the recipe ID for this item."""
        if self.recipe_id is None:  # Only fetch if not already cached
        # Check if the item ID has a hard-coded recipe ID
            if self.item_id in HARDCODED_RECIPES:
                self.recipe_id = HARDCODED_RECIPES[self.item_id]
                return self.recipe_id

            # Otherwise, query the API
            url = f"https://api.guildwars2.com/v2/recipes/search?output={self.item_id}"
            response = self.api_querier(url)

            if not response:
                return False
            else:
                self.recipe_id = response[0]  # Store the first recipe ID
                if debug_mode:
                    print(f"Recipe ID for {self.item_name} is {self.recipe_id}")
                return self.recipe_id
        return self.recipe_id

    def get_recipe_data(self):
        """Fetch and store the full recipe data for this item."""

        if self.recipe_id:
            url = f"https://api.guildwars2.com/v2/recipes?ids={self.recipe_id}&v=latest&lang=en"
            self.recipe_data = self.api_querier(url)[0]
            # Some recipes output more than 1 item, tracking that number here
            self.output_item_count = self.recipe_data.get("output_item_count", 1)

            if debug_mode:
                print(f"Recipe data for {self.item_name} is {self.recipe_data}")

            return self.recipe_data
        else:
            return False

    def fetch_ingredients(self):
        """
        Fetch the ingredients (children) for this item from the API.
        If the item has no recipe, it is considered a base (gatherable) item.
        """

        if self.base_ingredients is None:  # Only fetch if not already cached
            self.base_ingredients = {}  # Initialize as empty dictionary

        if self.recipe_data and "ingredients" in self.recipe_data:
            # Add children (base ingredients) to this item
            for ingredient in self.recipe_data["ingredients"]:
                if ingredient["type"] in ['Item', 'Currency']:
                    if ingredient["id"] in GLOBAL_ITEM_LIBRARY:
                        if debug_mode:
                            print(f"fetching {ingredient['id']} from global item library")
                        child_item = GLOBAL_ITEM_LIBRARY[ingredient["id"]]
                    else:
                        child_item = CraftingItem(ingredient["id"])
                        child_item.item_type = ingredient["type"]

                        # get data necessary for recursion
                        child_item.get_everything_child()

                        # child_item.get_everything_child()
                        GLOBAL_ITEM_LIBRARY[ingredient["id"]] = child_item # Add to global item library
                        
                    child_quantity = ingredient["count"] / self.output_item_count

                    self.base_ingredients[child_item] = child_quantity

                    if debug_mode:
                        print(f"ingredients for {self.item_name} are {self.base_ingredients}")
        else:
            # This is a base (gatherable) item with no children
            self.base_ingredients = {}

    def get_item_price(self):
        """
        Fetch the current buy price of this item from the API.
        """
        if self.item_type == "Currency":
            if self.item_id == 61:
                if debug_mode:
                    research_note_price = 0
                else:
                    print("Research Note price is currently not supported. Please enter the price manually.")
                    url = "https://fast.farming-community.eu/salvaging/costs-per-research-note"
                    webbrowser.open(url)
                    # There's no easy way to get the price of an individual research note. For now I'm asking for it explicitly. A future item would be automating this.
                    research_note_price = float(input("Enter the price per Research Note from https://fast.farming-community.eu/salvaging/costs-per-research-note: ")) / 10000
                self.price = research_note_price
                return self.price
            else:
                self.price = 0  # Non Research Note Currencies do not have a price, set to 0
                return self.price

        url = f"https://api.guildwars2.com/v2/commerce/prices/{self.item_id}"
        response = self.api_querier(url)

        if not response:
            print(f"Warning: Price not found for {self.item_name}, it is likely {self.item_name} is an account bound item")
            self.price = 0 # Set price to None if not found
            return False
        
        # For items not on TP, return default value (None)
        if not response.get("buys"):
            print(f"Warning: Price not found for {self.item_name}, it is likely {self.item_name} is an account bound item")
            self.price = 0
            return self.price

        self.volume = response["sells"]["quantity"] + response["buys"]["quantity"]

        self.price_instant = response["sells"]["unit_price"] / 10000

        self.price = response["buys"]["unit_price"] / 10000 if response["buys"]["unit_price"] != 0 else self.price_instant

        if debug_mode:
            print(f"Price for {self.item_name} is {self.price :.2f} gold")
            print(f"Instant price for {self.item_name} is {self.price_instant :.2f} gold")
            print(f"Volume for {self.item_name} is {self.volume}")

        return self.price   

    def get_raw_ingredients(self, eldest_raw_ingredients=None, parent_quantity=1, parent_id=None):
        """
        Recursively calculate the total base (gatherable) ingredients required to craft this item.
        """

        if eldest_raw_ingredients is None:
            eldest_raw_ingredients = {}

        if self.raw_ingredients is None:
            self.raw_ingredients = {}  # Initialize if not already done

        if parent_id is None:
            parent_id = self.item_id

        for child, quantity in self.base_ingredients.items():
            # Fetch the item name and price for the child

            child.get_everything_child()  

            # If the child has its own ingredients, recurse
            if child.base_ingredients:
                
                # In cases where a craftable item is nested inside another craftable item and the parent has a quantity greater than 1, we need to multiply the child's quantity by the parent's quantity
                if parent_id == self.item_id:
                    parent_quantity = quantity
                else:
                    parent_quantity = quantity * parent_quantity                

                parent_id = self.item_id

                # If the child has its own ingredients, recurse
                child.get_raw_ingredients(eldest_raw_ingredients, parent_quantity, parent_id)

            else:

                # There are cases where parent_quantity carries over from a previous iteration in recipes comprised of both base and non base ingredients, so we need to reset it
                if parent_id == self.item_id:
                    parent_quantity = 1
                
                if debug_mode:
                    print(f"attaching {quantity * parent_quantity} {child.item_name}'s to eldest_raw_ingredients in {self.item_name}")

                if child.item_id in eldest_raw_ingredients:
                    eldest_raw_ingredients[child.item_id]["amount_needed"] += quantity * parent_quantity
                else:
                    eldest_raw_ingredients[child.item_id] = {
                        "name": child.item_name,
                        "amount_needed": quantity * parent_quantity,
                        "unit_price": child.price 
                    }

        self.raw_ingredients = eldest_raw_ingredients

        self.raw_ingredients_dataframe = pd.DataFrame.from_dict(self.raw_ingredients, orient='index')

        if debug_mode:
            print(f"Total raw ingredients for {self.item_name} are {self.raw_ingredients}")

        return self.raw_ingredients
    
    
    def calculate_crafting_cost(self):
        """
        Calculate the total crafting cost of this item.
        """
        # Fetch the total ingredients if not already done
        if self.raw_ingredients is None:
            self.get_raw_ingredients()

        # Calculate the total crafting cost

        for item in self.raw_ingredients:
            if self.raw_ingredients[item]["unit_price"] == None:
                continue
            
            self.raw_ingredients[item]["total_cost"] = self.raw_ingredients[item]["amount_needed"] * self.raw_ingredients[item]["unit_price"]
            self.crafting_cost += self.raw_ingredients[item]["total_cost"]

        if debug_mode:
            print(f"Crafting cost for {self.item_name} is {self.crafting_cost :.2f} gold")
        
        return self.crafting_cost
    
    def calculate_profit_margin(self):
        """
        Calculate the profit margin of this item.
        """

        if self.price_instant is None or self.crafting_cost is None:
            raise ValueError("Price or crafting cost is not available for this item.")

        if debug_mode:
            print(f"price is {self.price :.2f} for a cost of {self.crafting_cost :.2f} gold")

        # 15% tax on selling price
        self.profit_margin_insta = (self.price * 0.85 - self.crafting_cost)
        self.profit_margin = (self.price_instant * 0.85 - self.crafting_cost) 
        
        print(f"Profit margin for {self.item_name} is {self.profit_margin} gold per item")

        return self.profit_margin
    
    def get_analysis_metrics(self):
        """
        Get all analysis metrics for this item. This helps inform decisions on what items to craft
        """
        # Fetch all data if not already done
        self.get_everything()

        self.metrics_dict["item_name"] = self.item_name
        self.metrics_dict["item_id"] = self.item_id
        self.metrics_dict["total_raw_resources"] = sum(item['amount_needed'] for item in self.raw_ingredients.values())
        self.metrics_dict["profit_margin"] = self.profit_margin

        self.metrics_dict["profit_per_raw"] = (
            self.metrics_dict["profit_margin"] / self.metrics_dict["total_raw_resources"]
            if self.metrics_dict["total_raw_resources"] != 0
            else 0
        )

        self.metrics_dict["profit_margin_insta"] = self.profit_margin_insta

        self.metrics_dict["profit_per_raw_insta"] = (
            self.metrics_dict["profit_margin_insta"] / self.metrics_dict["total_raw_resources"]
            if self.metrics_dict["total_raw_resources"] != 0
            else 0
        )

        self.metrics_dict["crafting_cost"] = self.crafting_cost 
        self.metrics_dict["price_sell"] = self.price_instant 
        self.metrics_dict["gap_%"] = 1 - (self.price / self.price_instant) if self.price_instant != 0 else 0
        self.metrics_dict["volume"] = self.volume

        for id in self.raw_ingredients:
            if self.raw_ingredients[id]['unit_price'] == 0:
                print(f"Warning: {self.item_name} has {self.raw_ingredients[id]['name']} as an ingredient, this is likely an account bound item/currency and will thus not be included in the profit margin calculation")

        return self.metrics_dict

    def __repr__(self):
        return f"CraftingItem(item_name = {self.item_name}, item_id={self.item_id}, recipe_id={self.recipe_id}, raw_ingredients={self.raw_ingredients})"