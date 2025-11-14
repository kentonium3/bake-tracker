# Feedback group 1: 

1. The design doc is focused specifically on consumption and inventory interactions but there are implications to how planning, inventory, "in progress", purchasing, and reporting workflows are represented in the app as a whole. We need to make sure the architecure and design as a whole is integral while breaking down required changes into very focused units of work that we can run through the spec-kitty workflow one at a time to build up the totality of required functionality.

2. What is currently called a "Finished Good" would be more accurately described as a "Finished Unit". What this describes or defines is a singular item consumable by a human that comes from a recipe batch. The purpose of a Finished Unit as a measure is to assist with the calculation of required batches of recipes and with the construction of bundles and packages. Examples of Finished Units of baked goods are a cookie, a piece of fudge, a truffle, a cake, a biscotti, a cracker. For other types of foods a Finished Unit would equate to a Serving. Examples are mousse au chocolate or othe puddings, chilis, stews, whipped cream, beans, rice, pasta, and sauces. In these cases a Finished Unit would be a quantity equal to a Serving. However, a Finished Unit is not necessarily a Serving. For example, a serving of crackers is some quantity of crackers. A Serving of french fries is some quantity of fries. A Serving is a term used to describe an assumed quantity per person a given batch of a recipe provides. Task: We should undertake an code-wide renaming of Finished Good to Finished Unit as a distinct task so the concept is clear.

3. Open question - "Finished Goods" is a term we could redefine as a category meaning "foods that are done". Yet, bundles that are made and completed Packages are  also made and completed. A batch of cookies made by a baker and brought to a fair is a Finished Good. More thought needs to be given to how this term is applied within the app. 

4. Open question - The draft spec states, "A `ProductionRun` represents the instantiation of a recipe with specific quantities and context". Is a production run defined as the execution of x batches of one recipe to fulfill the desired quantities. Or, is a Production Run defined as the execution of x batches of y recipies (Jobs or Tasks?) needed to fulfill the requirements of the goal (what we currently call an Event)? Having "Jobs" or "Tasks" run in sequence or in parallel, as resources enable, to complete a full Production Run for an event seems to map conceptually to what actually happens. 

5. The way a production run is described in the document it seems to take a first class, visible role (and term) as the planning entry point. I would rather we think of a production run more implicitly as an outcome of the planning of an event in its presentation. In other words, "production run" is a fairly industrial term. By comparison, home cooks and bakers would call it a "bake". I'm not proposing we use the term "bake" in the UI to mean "make several batches of goodies in a row", but I'd rather not use the term "production run" in the UI. (If and when we get to porting this to be a web application, then tokenizing all visible terms will be part of the plan to support localization and possibly verticalization of the app. Distant future feature.)

6. In the "1. CONSUMPTION INTEGRATION POINTS" section it seems my comments of a cook/baker saying "I want to make something." was interpreted to mean they somewhat randomly wanted to make a batch of something, but what I meant is that this is the cook/baker's first response to an external event or request of some sort.  There's always some sort of event as the trigger -- a holiday, a birthday, a work social event, an organized event such as a fair, a bake sale, a large dinner, or even an order. I do not see distinction in the consumption integration points EXCEPT in a potential future use case scenario where someone in a business might use this to plan regular production runs of a good for sale. We do not need to accommodate that use case yet, but the design should be extensible to allow it. Task: Rewrite that section to reflect this understanding. 
7. Section 2. MANUAL INVENTORY ADJUSTMENTS, section Enhanced Pantry "Adjust Mode" looks good though we do not need to have Reason Codes at this point. Task: Make inventory adjustment reason codes a future feature.

8. Open design question - recipe scaling. 
   - Recipe scaling is more complicated than it may appear because not all ingredients scale linearly for all recipes. For now, let's assume the cook/baker will simply make as many batches as needed to fulfill the quantity required. They can decide to make double batches (a common home baker practice when needed) on their own. The app does not need to reflect this decision. 
   - Recipe ingredient substitution. This is common, but for now we will leave it to the cook/baker to either create a new recipe, or edit the existing recipe (in which case, I suspect the recipe would actually need to be cloned to retain relational and reporting integrities, so a new recipe would result anyway. ) 
   - This all hints at a future, more sophisticated treatment of a recipe as an object with scaling properties, potential substitute ingredients, or whole variants of the recipe. 
   - Recipes will likely need additional attributes such as source (web, magazine, person, etc), attribution (ie. Bake From Scratch, Bon Appetit), url, and related entities such as images, nutrition info, required equipment, and more. All future features. 
   - Any equipment requirements or constraints will be up to the human to figure out for now. 
   
9. How do events relate to production runs?
   - Assume production runs are associated with a single event. We do not need to consider a scale where a production run may serve multiple events at this point.

10. When and how do we create finished goods inventory?
- First, I like the idea of a "finished goods inventory" which you introduced. 
- Second, recall that we need to redefine Finished Goods as it is currently used to instead be Finished Units. If we use a new definition of Finished Goods then this is how a cook/baker thinks of "Finished Goods":
	- The foods I need to make. 
		- The total number of discrete items I've finished cooking -- cookies, candies, etc.
		- The total number of cakes and pies I've finished cooking no matter how many batches were required to make them.
	- The groupings I need to make from the food I've made.
		- The number of bundles I've made from the discrete items.
		- The number of packages I've made including all of the above. 

11. I agree with the "high-density everywhere" UI approach. 

12. I believe I answered most of the open questions. Refactor the proposed changes in design based on this input and we'll see what additional questions are left to address. 

# Feedback group 2

1.  Production run vs "Event run"?
	- We still need to align on what a "production run" is though. If you look at #4 in my initial feedback, I suggest a "production run" consist  of all the cooking tasks ("Jobs"? "Tasks"?) needed to fill all the output requirements for an event, but maybe this isn't the right term to use to describe it. I'm open to "production run" referring to making multiple batches of a recipe to fulfill a requirement but perhaps `RecipeProductionRun` is better. We need another term to describe the collection of recipe production runs needed to fulfill the requirements of an event. I nominate `EventProductionRun`as the collective term.  
2. `ProductionRun` Internal Structure (Decision Needed)
	- Tracking completion by the "Option B: ProductionRun is always single batch, create multiple ProductionRuns for quantity" you suggested makes sense to me. This allows the baker to know how much more they need to make at any one point. We'd need to rename this to be `RecipeProductionRun` if we adopt this pattern
3. Finished Goods Inventory Granularity (Decision Needed)
	- What matters is how many items of each type have been produced *relative* to what's needed in terms of total items required by the event. If you look at #10 in the group 1 feedback I suppose I described it as individual item tracking, but then also tracked by completed bundles and packages
	- "Considerations: Storage location, expiration tracking, partial consumption". None of these need to be considered at this point. In fact, we can drop "location" from the Pantry UI, too. Not needed at this point. 
4. Bundle/Package Workflow Integration (Unclear)
	- The production flow is generally, 
		- Cook/bake all the items needed for an event.
		- Assemble bundles from what's been cooked/baked.
		- Assemble packages from the finished goods, like cakes, and from bundles of discrete items.
	- I think what this means for the Production Workflow Model is there is a new "Assembly" step between steps 2 & 3 as currently documented in the design doc. 