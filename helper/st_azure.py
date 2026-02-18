import base64
import json
import streamlit as st

def get_azure_user():
    """
    Extracts Azure AD authenticated user details from platform headers.
    Works in Azure App Service, Container Apps, and Azure Static Web Apps.
    Returns:
        {
            "oid": "<aad-object-id>",
            "email": "<user@domain.com>",
            "name": "<Friendly Name>"
        }
    """
    # Try Streamlit's context headers first (requires Streamlit >= 1.18.0)
    headers = None
    try:
        headers = st.context.headers
    except (AttributeError, RuntimeError):
        # Fallback to checking environment (though headers won't be there)
        pass
    
    if not headers:
        return None   # No authenticated user
    
    # Azure Container Apps provides direct header shortcuts
    user_email = headers.get("X-Ms-Client-Principal-Name")
    user_id = headers.get("X-Ms-Client-Principal-Id")
    
    # If direct headers exist, use them (faster path)
    if user_email and user_id:
        return {
            "oid": user_id,
            "email": user_email,
            "name": user_email.split("@")[0],  # Best guess from email
        }
    
    # Fall back to parsing the full principal for more complete data
    principal_header = headers.get("X-Ms-Client-Principal") or headers.get("x-ms-client-principal")
    if not principal_header:
        return None
    
    try:
        # Decode base64 JSON
        decoded = base64.b64decode(principal_header).decode("utf-8")
        principal = json.loads(decoded)
        
        # Parse claims array to extract user details
        claims = principal.get("claims", [])
        
        def get_claim_value(claim_type):
            """Extract value from claims array by type."""
            for claim in claims:
                if claim.get("typ") == claim_type:
                    return claim.get("val")
            return None
        
        # Extract standard claims
        email = get_claim_value("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress")
        name = get_claim_value("name")
        oid = get_claim_value("http://schemas.microsoft.com/identity/claims/objectidentifier")
        
        return {
            "oid": oid,
            "email": email,
            "name": name,
        }
    except Exception as e:
        # Return error info for debugging
        return {
            "error": str(e),
            "raw_header": principal_header[:50] + "..." if len(principal_header) > 50 else principal_header
        }