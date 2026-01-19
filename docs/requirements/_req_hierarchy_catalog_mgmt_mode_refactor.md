**Ingredient and Materials listing**
- Problem: Current scheme conflates hierarchy management and normal user usage of Ingredient and Material items. Listing of bare L2 and L1 items is confusing to user.
- UX issue: Ingredient and Materials listings should show L2 items only, but with their associated L0/L1 parents for reference. 
- Future fit alignment: In web/multi-user function Ingredient and Material catalogs would be system level resources with user additions tracked separately with periodic incorporation of vetted user supplied changes into the main catalog. System admin level function.

**Category Management**
- This is an Administrative function in the local user app, not a regular user function.
- Category lists are needed for:
	- Ingredients - 3 tier (current)
	- Food Products (Inherits Ingredient categories)
	- Finished Unit (planned)
	- Finished goods (missing, regression)
	- Materials - 3 tier (current)
	- Material Unit (planned)
	- Material Products (Inherits Ingredient categories)
	- Recipes (future)
- Management of these lists should be separate from using these lists.

**Ingredient and Materials Mgmt**
- Needs two-tier management
	- "Edit copy" (copy of Production copy, save in OPML format?)
		- L0 add, rename
		- L0 remove with L1 remap tracking
		- L1 add, rename
		- L1 move to new L0 parent with remap tracking
		- L1 remove with enforced remap of children to new L1 with remap tracking
		- L2 move to new L1 parent with remap tracking
	- Save / Save & Apply
		- Saves working copy state for future edit
		- Propagate - propagates tracked remappings across related Food Products, Materials Products, and Recipes
	- "Production copy"
		- Results from Save & Apply edits of the working copy OR
		- from a json import/remap function
- Issues: 
	- Do not want to build an OPML editor. Need some semi-manual solution for using DynaList.io to manage the hierarchies to create the OPML, do the mapping, and producing an import file. Perhaps this means the Edit Copy exists outside the app for now. Needs discussion.
	- Need a function to import updated Ingredient and Materials hierarchies where the JSON  includes remapping info and where it validates the import and performs the remapping on related entities.
	- This is likely the point where Ingredients and Material hierarchies need semantic versioning.

 **Other UI changes**
- The top section of the mode tab is not useful and uses up valuable screen space. On the Catalog tab this is where "CATALOG 0 Ingredients 0 Products 0 Recipes" appears. Broken and not useful even if it worked. 
- The menu in the Catalog tab is not rational.
	- Currently shows Ingredients, Products, Recipes, Finished Units, Finished Goods, Packages, and Materials. 
	- Materials has sub-menus Materials Catalog, Material Products, and Material Units
	- For navigation inside Catalog mode it would make more sense to have:
		- Ingredients
			- Ingredient Catalog
			- Food Products
		- Materials
			- Material Catalog
			- Material Units
			- Material Products
		- Recipes
			- Recipes Catalog
			- Finished Units (because these are defined on recipes now, this would be a listing)
		- Packaging
			- FinishedGoods (Food Only)
			- FinishedGoods (Bundles)
			- Packages
- The Purchase submenu items are ordered Shopping Lists, Purchases, Inventory. 
		- This should be flipped to Inventory, Purchases, Shopping, Lists
- The Catalog / Inventory tab has a tree view. This is not needed and it can be removed.

**Mode refactor**
- Problem: UI still doesn't reflect realistic user mental mode
- Current Modes are: Catalog, Plan, Purchase, Make, Observe
- Catalog & Observe represent a library function and a dashboard function, but not a "doing" function.
- For now a better mental model fit would be:
	- Observe
	- Catalog
	- Plan
	- Purchase
	- Make
	- Deliver
- Plan, Purchase, Make, Deliver represent the essential activities involved in a bake/cook cycle.
- Under Deliver you would be the recipient list and packaging workflow items depending on the output mode. This is vague because these functions are not yet defined. 

**Packages/Packaging/Shipping/Output modes
- Catalog / Packages seems misplaced.
	- FinishedGoods allows us to define a) a food, like a cake, as a finished good b) a bundle of FinishedUnits + materials as a Finishedgood, such as a bag or pastry box of cookies.
	- Packages, as in collections of FinishedGoods for deliveries feels different. Within the scope of this single household, creating packages happens in the delivery step where collections of FinishedGoods are boxed up for shipment before being taken to the shipper. It is a form of "assembly" but its a separate activity from creating the bundles to ship. It's "packaging" in the shipper/shipment sense and not in the creation of the items being delivered.
- Output modes and ideas for how to represent them at the Delivery stage are TBD.

**Overall Priorities
- Getting the data model right and having the tools to rapidly iterate on data structure and data content changes is foundational since all other functions operate from it. 
- The Plan, Purchase, and Make workflows are the essential functions to get working after the data parts are sufficiently matured. These still need a lot of work. 
- Most of the current entity edit functions are currently broken.
- Not enough of the app is built and functional enough to perform a complete workflow cycle. This means the data model will continue to evolve and revisiting past decisions will continue to occur until a complete workflow cycle can be demonstrated. 