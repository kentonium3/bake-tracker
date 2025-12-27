**12/16/2025**

* My Ingredients display almost unusable.
	* Hundreds of items, only shows four at a time
	* Information need to be much denser
	* Scroll bar needs to move window contents much more granularly
	* Categories inline with ingredient name is useless. 
	* Random order of ingredients is useless.
	* Need to be able to search/sort/filter by name and category
* Products listing unusable
	* On-screen density is good but scroll bar doesn't seem to move the contents
	* Location column not needed
	* Need to be able to search/sort/filter by name and category
	* Has a "Consume Ingredient" button but these are Products not Ingredients.
	* Product name column is showing the brand and it is concatenated with the package size. 
	* Column showing the ingredient display name, brand, and a column of product_unit_quantity and product_unit concatenated would make more sense. 
	* "Quantity" column is not intuitive to decipher. Maybe "Remaining quantity" would be better. Need to figure out how to represent something like 2.5 bags of flour (12.5 lbs) where both whole and partial packages are represented along with the total quantity.
* Import error summary
	* Display extends past bottom of the screen
	* Can't move the error dialogue window
	* No way to clear the display of the error dialogue
	* No easy way to capture the error.
	* Needs to write it to a log

12/27/2025

- Ingredients
	- combine "poppy seeds, blue" -> "poppy seeds"
	- Some products have ingredients that are not in the ingredient list anymore. Looks like consolidated ingredient mapping wasn't applied to products.
- My Ingredients tab
	- Category filter doesn't work. Anything but All shows blank list. Incredibly slow to refresh the list. 
	- Make the Ingredients tab listing work like the Products tab listing -- full list scroll, double click to edit, delete button on edit form, more responsive, denser listing.
	- Search should treat diacriticals as english equivalent. (searching for "creme" should also find "crème)
	- When editing an ingredient, the categories in the edit form are different than the categories in the category drop down on the ingredient list filter and everywhere else. It should be using the same list.
- My Pantry tab
	- Make the inventory listing work like the Products tab listing -- full list scroll, double click to edit, delete button on edit form, more responsive, denser listing.
- My Products tab
	- Has a "Manage Suppliers" button that results in "Coming soon!" Should invoke the same function as File > Manage Suppliers
	- Product Detail and Edit form missing package type (jar, bag, can, etc.)
	- Edit product form should validate package unit or provide drop-down. 
	- Switch order of package_unit and package_unit_quantity on form
- 