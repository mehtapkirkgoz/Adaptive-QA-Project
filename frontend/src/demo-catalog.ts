// Accepted catalog definitions for a non-executing public demo.
export const demoCatalog = [
  {
    "case_id": "LOGIN-001",
    "name": "Login form is visible",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "The user identifier field, password field, and login submit button are visible.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-002",
    "name": "Username is required",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "Username validation blocks submission and no result is displayed.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-003",
    "name": "Password is required",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "Password validation blocks submission and no result is displayed.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-004",
    "name": "Demo login submission displays its status",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "The demo-only authentication status is displayed without network submission.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-001",
    "name": "Search form is available",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "The search field is visible and the Search button is enabled.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-002",
    "name": "Search displays the no-results message",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "The status message is: No products found for \"sample book\".",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-003",
    "name": "Search query is required",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "Query validation blocks submission and no result is displayed.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-004",
    "name": "Whitespace search displays a prompt",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "The result status asks the user to enter a search term.",
    "changes_data": false
  },
  {
    "case_id": "NAV-001",
    "name": "Login link navigates to its section",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "The URL ends with #login and the login section is in the viewport.",
    "changes_data": false
  },
  {
    "case_id": "NAV-002",
    "name": "Search link navigates to its section",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "The URL ends with #search and the search section is in the viewport.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-005",
    "name": "Username rejects invalid characters",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "A username containing spaces has patternMismatch=true.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-006",
    "name": "Short password blocks submission",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "A five-character password has tooShort=true and no login result is displayed.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-007",
    "name": "Enter submits the demo login",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "Enter in the password field publishes the fixed demo-only login status.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-008",
    "name": "Login reset clears inputs and result",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "Login reset empties both credentials and the prior result.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-009",
    "name": "Login reset preserves independent search state",
    "test_type": "ui",
    "required_features": [
      "login",
      "search"
    ],
    "expected_result": "Login reset preserves the existing search query.",
    "changes_data": false
  },
  {
    "case_id": "LOGIN-010",
    "name": "Password visibility toggle restores masking",
    "test_type": "ui",
    "required_features": [
      "login"
    ],
    "expected_result": "The toggle reveals then masks the password without changing its value.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-005",
    "name": "Enter submits search",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "Enter publishes the literal no-results message for sample book.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-006",
    "name": "Search reset clears query and result",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "Search reset empties the query and previous result.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-007",
    "name": "Search enforces its input length limit",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "Inserting 70 characters retains exactly the configured 64-character maximum.",
    "changes_data": false
  },
  {
    "case_id": "SEARCH-008",
    "name": "Search renders markup as literal text",
    "test_type": "ui",
    "required_features": [
      "search"
    ],
    "expected_result": "Markup is displayed literally in the result and creates no image element.",
    "changes_data": false
  },
  {
    "case_id": "FORM-001",
    "name": "Email rejects malformed addresses",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "A malformed email has typeMismatch=true.",
    "changes_data": false
  },
  {
    "case_id": "FORM-002",
    "name": "Email accepts a valid address",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "qa@example.test has valid=true in the email control.",
    "changes_data": false
  },
  {
    "case_id": "FORM-003",
    "name": "Required agreement blocks submission",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Unchecked required agreement has valueMissing=true and prevents a result.",
    "changes_data": false
  },
  {
    "case_id": "FORM-004",
    "name": "Agreement checkbox toggles",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Checking then unchecking updates the agreement checkbox state.",
    "changes_data": false
  },
  {
    "case_id": "FORM-005",
    "name": "Delivery radio choices are exclusive",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Selecting express delivery unchecks standard delivery.",
    "changes_data": false
  },
  {
    "case_id": "FORM-006",
    "name": "Country selection persists",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Selecting Turkey retains the tr option value.",
    "changes_data": false
  },
  {
    "case_id": "FORM-007",
    "name": "Notes retain multiple lines",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "The textarea preserves both entered lines and their newline.",
    "changes_data": false
  },
  {
    "case_id": "FORM-008",
    "name": "Quantity rejects values below minimum",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Quantity 0 has rangeUnderflow=true.",
    "changes_data": false
  },
  {
    "case_id": "FORM-009",
    "name": "Quantity rejects values above maximum",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Quantity 11 has rangeOverflow=true.",
    "changes_data": false
  },
  {
    "case_id": "FORM-010",
    "name": "Quantity rejects a fractional step",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Quantity 1.5 has stepMismatch=true for integer steps.",
    "changes_data": false
  },
  {
    "case_id": "FORM-011",
    "name": "Quantity accepts an in-range integer",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Quantity 5 has valid=true.",
    "changes_data": false
  },
  {
    "case_id": "FORM-012",
    "name": "Disabled input rejects editing",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Disabled input rejects fill and preserves its initial value.",
    "changes_data": false
  },
  {
    "case_id": "FORM-013",
    "name": "Read-only input rejects editing",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Read-only input rejects fill and preserves its initial value.",
    "changes_data": false
  },
  {
    "case_id": "FORM-014",
    "name": "Reset restores native control defaults",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Reset restores unchecked agreement, standard delivery, gb, quantity 1, and empty notes.",
    "changes_data": false
  },
  {
    "case_id": "FORM-015",
    "name": "Invalid submission leaves result empty",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Empty email prevents submission and leaves the result empty.",
    "changes_data": false
  },
  {
    "case_id": "FORM-016",
    "name": "Valid control form publishes its result",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Valid email and agreement produce exactly Demo controls submitted.",
    "changes_data": false
  },
  {
    "case_id": "NAV-003",
    "name": "Enter activates the login link",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "Enter on the login link navigates to the login fragment.",
    "changes_data": false
  },
  {
    "case_id": "NAV-004",
    "name": "Navigation exposes named visible links",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "Both visible navigation links have names and the expected fragment targets.",
    "changes_data": false
  },
  {
    "case_id": "NAV-005",
    "name": "Section navigation preserves form input",
    "test_type": "ui",
    "required_features": [
      "navigation",
      "login"
    ],
    "expected_result": "Navigating to search preserves the entered username.",
    "changes_data": false
  },
  {
    "case_id": "NAV-006",
    "name": "Back restores the previous section",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "Back from search restores the previous login fragment.",
    "changes_data": false
  },
  {
    "case_id": "DOC-001",
    "name": "Document title is non-empty",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "The title contains non-whitespace text.",
    "changes_data": false
  },
  {
    "case_id": "DOC-002",
    "name": "Document language is declared",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "The language attribute contains non-whitespace text.",
    "changes_data": false
  },
  {
    "case_id": "DOC-003",
    "name": "Document IDs are unique",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "All IDs are non-empty and unique.",
    "changes_data": false
  },
  {
    "case_id": "DOC-004",
    "name": "ARIA references resolve",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "Every declared ARIA reference resolves to an element.",
    "changes_data": false
  },
  {
    "case_id": "DOC-005",
    "name": "Fragment links resolve",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "Each non-empty local fragment has an ID or named anchor target.",
    "changes_data": false
  },
  {
    "case_id": "A11Y-001",
    "name": "Visible buttons have accessible names",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "Every visible button has a non-whitespace accessible name.",
    "changes_data": false
  },
  {
    "case_id": "A11Y-002",
    "name": "Visible form controls have accessible names",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Every visible form control has a non-whitespace accessible name.",
    "changes_data": false
  },
  {
    "case_id": "NAV-007",
    "name": "Visible links have accessible names",
    "test_type": "ui",
    "required_features": [
      "navigation"
    ],
    "expected_result": "Every visible link has a non-whitespace accessible name.",
    "changes_data": false
  },
  {
    "case_id": "FORM-017",
    "name": "Explicit labels target labelable controls",
    "test_type": "ui",
    "required_features": [
      "forms"
    ],
    "expected_result": "Every explicit label targets an existing labelable control.",
    "changes_data": false
  },
  {
    "case_id": "DOC-006",
    "name": "Viewport preserves zoom",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "No viewport directive disables zoom or caps maximum scale below two.",
    "changes_data": false
  },
  {
    "case_id": "DOC-007",
    "name": "Document does not force meta refresh",
    "test_type": "ui",
    "required_features": [],
    "expected_result": "No meta refresh directive replaces the page automatically.",
    "changes_data": false
  },
  {
    "case_id": "API-001",
    "name": "Health reports readiness",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 200 with ready=true.",
    "changes_data": false
  },
  {
    "case_id": "API-002",
    "name": "Catalog returns structured items",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Two typed items with integer IDs and numeric prices.",
    "changes_data": false
  },
  {
    "case_id": "API-003",
    "name": "Known item returns its identity",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Item 1 is Notebook with price 10.",
    "changes_data": false
  },
  {
    "case_id": "API-004",
    "name": "Missing item returns not found",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 404 with item_not_found.",
    "changes_data": false
  },
  {
    "case_id": "API-005",
    "name": "Search returns matching items",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "One Notebook match.",
    "changes_data": false
  },
  {
    "case_id": "API-006",
    "name": "Unmatched search returns an empty list",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "An empty items array and count zero.",
    "changes_data": false
  },
  {
    "case_id": "API-007",
    "name": "Missing search query is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 400 with query_required.",
    "changes_data": false
  },
  {
    "case_id": "API-008",
    "name": "Excessive query length is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with query_too_long.",
    "changes_data": false
  },
  {
    "case_id": "API-009",
    "name": "Anonymous private access is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 401 with authentication_required.",
    "changes_data": false
  },
  {
    "case_id": "API-010",
    "name": "Configured bearer grants private access",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 200 with authenticated=true.",
    "changes_data": false
  },
  {
    "case_id": "API-011",
    "name": "Insufficient scope is forbidden",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 403 with insufficient_scope.",
    "changes_data": false
  },
  {
    "case_id": "API-012",
    "name": "HEAD succeeds without body assertions",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 200; HEAD requires no JSON body.",
    "changes_data": false
  },
  {
    "case_id": "API-013",
    "name": "Unsupported method is reported by the API",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 405 with method_not_allowed.",
    "changes_data": false
  },
  {
    "case_id": "API-014",
    "name": "Valid echo request is accepted",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 201 echoes the configured name and accepted=true.",
    "changes_data": true
  },
  {
    "case_id": "API-015",
    "name": "Missing required payload field is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with invalid_name.",
    "changes_data": true
  },
  {
    "case_id": "API-016",
    "name": "Oversized payload field is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with invalid_name.",
    "changes_data": true
  },
  {
    "case_id": "API-017",
    "name": "Quantity below minimum is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with invalid_quantity.",
    "changes_data": true
  },
  {
    "case_id": "API-018",
    "name": "Valid quantity satisfies the business total",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Quantity three yields total 30.",
    "changes_data": true
  },
  {
    "case_id": "API-019",
    "name": "Quantity above maximum is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with invalid_quantity.",
    "changes_data": true
  },
  {
    "case_id": "API-020",
    "name": "Redirect response is observed without following",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 307 is returned without a second request or credential forwarding.",
    "changes_data": false
  },
  {
    "case_id": "API-021",
    "name": "Pagination returns the requested window and terminal cursor",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "The second item is returned with total two and no next offset.",
    "changes_data": false
  },
  {
    "case_id": "API-022",
    "name": "Invalid pagination is rejected before slicing",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 400 with invalid_pagination.",
    "changes_data": false
  },
  {
    "case_id": "API-023",
    "name": "Price sorting returns ascending numeric values",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Pencil at two precedes Notebook at ten.",
    "changes_data": false
  },
  {
    "case_id": "API-024",
    "name": "Category taxonomy exposes stable identifiers",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Paper and writing categories have distinct stable IDs.",
    "changes_data": false
  },
  {
    "case_id": "API-025",
    "name": "Category filter excludes unrelated inventory",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Only Pencil belongs to the writing category.",
    "changes_data": false
  },
  {
    "case_id": "API-026",
    "name": "Available inventory exposes its usable quantity",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Notebook is available with eight units.",
    "changes_data": false
  },
  {
    "case_id": "API-027",
    "name": "Zero inventory prevents an availability claim",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Pencil has zero stock and available=false.",
    "changes_data": false
  },
  {
    "case_id": "API-028",
    "name": "Empty cart cannot proceed to checkout",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "No lines, zero total and checkout_enabled=false.",
    "changes_data": false
  },
  {
    "case_id": "API-029",
    "name": "Cart line and subtotal agree with configured quantity and price",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Two units at ten yield line total and subtotal twenty.",
    "changes_data": false
  },
  {
    "case_id": "API-030",
    "name": "Discount reduces the payable total without changing the subtotal",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Ten percent of twenty is two, leaving eighteen payable.",
    "changes_data": false
  },
  {
    "case_id": "API-031",
    "name": "Delivery quote includes the configured region and currency",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "TR delivery costs five TRY.",
    "changes_data": false
  },
  {
    "case_id": "API-032",
    "name": "Unsupported delivery region is rejected",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with unsupported_region.",
    "changes_data": false
  },
  {
    "case_id": "API-033",
    "name": "Validation errors identify the affected field",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "HTTP 422 with an email-specific invalid_email error.",
    "changes_data": false
  },
  {
    "case_id": "API-034",
    "name": "Authenticated profile preserves nullable and false-valued fields",
    "test_type": "api",
    "required_features": [
      "api"
    ],
    "expected_result": "Profile seven includes a null avatar and newsletter=false.",
    "changes_data": false
  },
  {
    "case_id": "DB-001",
    "name": "Product primary key lookup",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Product primary key lookup satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-002",
    "name": "Unknown product returns no rows",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Unknown product returns no rows satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-003",
    "name": "Catalog contains three products",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Catalog contains three products satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-004",
    "name": "Stored product price matches",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Stored product price matches satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-005",
    "name": "Out of stock product remains identifiable",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Out of stock product remains identifiable satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-006",
    "name": "Available stock excludes unavailable products",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Available stock excludes unavailable products satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-007",
    "name": "Unicode product lookup",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Unicode product lookup satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-008",
    "name": "Order belongs to its customer",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Order belongs to its customer satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-009",
    "name": "Paid order status is persisted",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Paid order status is persisted satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-010",
    "name": "Customer filter isolates orders",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Customer filter isolates orders satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-011",
    "name": "Optional order note preserves null",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Optional order note preserves null satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-012",
    "name": "Order line quantities aggregate",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Order line quantities aggregate satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-013",
    "name": "Order total follows stored line prices",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Order total follows stored line prices satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-014",
    "name": "Order lines reference existing products",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "Order lines reference existing products satisfies its explicit assertion.",
    "changes_data": false
  },
  {
    "case_id": "DB-015",
    "name": "SQL-like customer input remains literal",
    "test_type": "database",
    "required_features": [
      "database"
    ],
    "expected_result": "SQL-like customer input remains literal satisfies its explicit assertion.",
    "changes_data": false
  }
];
