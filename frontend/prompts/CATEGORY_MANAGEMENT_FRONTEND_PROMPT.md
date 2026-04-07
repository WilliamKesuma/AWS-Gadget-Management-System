# Frontend Implementation Prompt — Asset Category Management

## Context

You are building the React frontend for Asset Category Management in the Gadget Management System. The backend API is fully implemented. Categories are now dynamic DynamoDB records instead of a hardcoded enum. Management users can create and delete categories at runtime. The `category` field on assets is now a plain `string` instead of a fixed enum.

This feature adds a "Manage Categories" dialog accessible from the `/assets` page for management users, and updates the Create Asset form to use a dynamic category dropdown.

---

## API Endpoints

| Method | Path | Role(s) | Purpose |
| --- | --- | --- | --- |
| POST | `/categories` | management | Create a new asset category |
| DELETE | `/categories/{category_id}` | management | Delete an existing category |
| GET | `/categories?page=&page_size=` | management | List all categories (paginated) |

---

## TypeScript Types (already defined in `types.ts`)

```typescript
type CategoryItem = {
    category_id: string
    category_name: string
    created_at: string
}

type CreateAssetCategoryRequest = {
    category_name: string
}

type CreateAssetCategoryResponse = {
    category_id: string
    category_name: string
    created_at: string
}

type ListAssetCategoriesResponse = PaginatedAPIResponse<CategoryItem>

// Existing types updated — category is now `string` instead of a fixed enum:
// CreateAssetRequest.category: string
// AssetItem.category?: string
// GetAssetResponse.category?: string
// ListAssetsFilter.category?: string
```

---

## Features to Implement

### 1. Manage Categories Dialog (Management only)

**Render condition:** `role === "management"`

On the `/assets` page, add a "Manage Categories" button (e.g., a gear/settings icon button or a text button near the page header/filters area).

Clicking it opens a Dialog (shadcn `Dialog`) with the title "Manage Categories". The dialog contains:

#### Category List

Fetch categories from `GET /categories` on dialog open. Display them in a table or list:

| Column | Field | Notes |
| --- | --- | --- |
| Category Name | `category_name` | Display as-is (SCREAMING_SNAKE_CASE) or format for readability (e.g., "MOBILE_PHONE" → "Mobile Phone") |
| Created At | `created_at` | Formatted date |
| Actions | — | Delete button (trash icon) |

Include pagination controls if there are many categories.

If no categories exist, show: "No categories found. Add one below."

#### Add Category Form

Below the category list, show an inline form:

- **Category Name** — text input (required, cannot be blank)
- **"Add Category"** — submit button

On submit, call `POST /categories` with `{ category_name: inputValue }`.

The backend automatically converts the input to SCREAMING_SNAKE_CASE (e.g., "Mobile Phone" → "MOBILE_PHONE"), so the user can type in any format.

On success:
- Show a success toast: "Category '{category_name}' created."
- Clear the input field.
- Refresh the category list within the dialog.

Handle these error cases:
- 400: "category_name is required" — show inline validation error.
- 409: "Category '{NAME}' already exists" — show a toast or inline error indicating the duplicate.
- 403: "You are required to have management role" — should not happen if render condition is correct, but handle gracefully.

#### Delete Category

Each category row has a delete button (trash icon, styled as destructive/ghost).

Clicking it opens a confirmation alert dialog: "Are you sure you want to delete '{category_name}'? Existing assets with this category will not be affected."

On confirm, call `DELETE /categories/{category_id}`.

On success:
- Show a success toast: "Category '{category_name}' deleted."
- Refresh the category list within the dialog.

Handle these error cases:
- 404: "Category not found" — the category may have already been deleted. Refresh the list.
- 403: "You are required to have management role" — handle gracefully.

---

### 2. Dynamic Category Dropdown on Create Asset Form

**Render condition:** `role === "it-admin"` (Create Asset is an IT Admin action)

On the Create Asset form, replace the hardcoded category dropdown (which previously used the fixed `AssetCategory` enum values: LAPTOP, MOBILE_PHONE, TABLET, OTHERS) with a dynamic dropdown that fetches categories from the API.

On form load, call `GET /categories?page_size=100` to fetch all available categories.

Populate a `Select` (shadcn) component with the results:
- Display value: `category_name` (formatted for readability, e.g., "MOBILE_PHONE" → "Mobile Phone", or display as-is)
- Submit value: `category_name` (the SCREAMING_SNAKE_CASE string, e.g., "MOBILE_PHONE")

If the categories API call fails or returns empty, show a fallback message in the dropdown: "No categories available. Contact management to add categories."

The `category` field is required on `CreateAssetRequest`. If no category is selected, disable the submit button or show a validation error.

---

### 3. Dynamic Category Filter on Assets List

**Render condition:** All roles that can view the assets list

On the `/assets` list page, the existing category filter dropdown should also be updated to use dynamic categories instead of the hardcoded enum.

On page load (or when the filter section mounts), call `GET /categories?page_size=100` to fetch all available categories.

Populate the category filter dropdown with:
- An "All" option (no filter applied)
- One option per category from the API response

The filter value sent as `category` query param to `GET /assets` should be the `category_name` string (e.g., "LAPTOP").

---

## Conditional Rendering Summary

| Component / Action | it-admin | management | employee | finance |
| --- | --- | --- | --- | --- |
| "Manage Categories" button on /assets page | ❌ | ✅ | ❌ | ❌ |
| Manage Categories dialog (list, add, delete) | ❌ | ✅ | ❌ | ❌ |
| Dynamic category dropdown on Create Asset form | ✅ | ❌ | ❌ | ❌ |
| Dynamic category filter on Assets list | ✅ | ✅ | ✅ | ✅ |

---

## Component Structure Suggestion

```
/assets page
├── "Manage Categories" button (management only)
│   └── ManageCategoriesDialog
│       ├── CategoryList (table with delete buttons + pagination)
│       └── AddCategoryForm (inline input + submit)
├── Asset filters bar
│   └── Category filter dropdown (dynamic, all roles)
└── Assets table
```

---

## UX Details

- The "Manage Categories" button should be visually distinct but not dominant — a secondary/outline button or an icon button with a tooltip works well. Place it near the filters or page header.
- Category names from the API are in SCREAMING_SNAKE_CASE (e.g., "MOBILE_PHONE"). For display purposes, you may format them for readability (replace underscores with spaces, title case: "Mobile Phone"). When submitting to the API (create asset, filter), always use the raw `category_name` value.
- The Add Category input should have a placeholder like "e.g., Monitor, Printer, Headset".
- The delete confirmation should clearly state that existing assets are not affected.
- Keep the dialog a reasonable size — it should not feel like a full page. A medium-width dialog with a scrollable category list works well.
- When the dialog is closed and categories were modified (added or deleted), refresh the category filter dropdown on the assets list page to reflect the changes.

---

## Notes

- The `GET /categories` endpoint requires the `management` role. For the dynamic category dropdown on the Create Asset form (IT Admin) and the category filter (all roles), you have two options:
  1. Cache categories in a shared context/store that management populates.
  2. Add a public/shared endpoint for listing categories (not yet implemented — for now, hardcode a fallback or fetch from the management-scoped endpoint if the user also has management access).
  
  **Recommended approach:** Since IT Admins and other roles also need the category list for the dropdown/filter, fetch categories on the assets page load. If the user doesn't have management access and the API returns 403, fall back to displaying whatever categories are already present in the loaded assets list (extract unique `category` values from the asset items). This provides a graceful degradation.

- The backend converts any input to SCREAMING_SNAKE_CASE on creation. "mobile phone", "Mobile Phone", and "MOBILE_PHONE" all produce the same category. The duplicate check is based on the formatted name.
- Deleting a category does NOT affect existing assets. Assets that reference the deleted category will still display it. The category simply won't appear in the dropdown for new asset creation.
- All list endpoints support pagination with `page` and `page_size` query parameters. Default is page 1, 20 items per page. For the category dropdown/filter, use `page_size=100` to fetch all categories in one call (unlikely to exceed 100 categories).
- The `created_at` field on `CategoryItem` is an ISO-8601 UTC timestamp. Format it consistently with the rest of the app (e.g., "Mar 25, 2026").
