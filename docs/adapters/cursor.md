# Cursor IDE Adapter

## Status

**Note**: Cursor IDE does not currently have a public API. This adapter is prepared for future API availability or can be used with Cursor's local integration features.

## Current Implementation

The adapter is structured to work with:
1. **Future Public API**: When Cursor releases a public API, update the `base_url` and endpoints
2. **Local Integration**: Connect to a local Cursor instance if available
3. **Extension Integration**: Work with Cursor extensions/plugins

## Configuration

Set environment variables:
- `CURSOR_API_URL`: Base URL for Cursor API (default: `http://localhost:3000`)
- `CURSOR_API_KEY`: API key if required

## Alternative Integration Methods

If Cursor doesn't provide a public API, consider:
1. **Cursor Extension**: Create a Cursor extension that exposes an API
2. **Local Server**: Run a local server that Cursor can connect to
3. **File-based Integration**: Use file watching and command execution

## Future Updates

When Cursor API becomes available:
1. Update `base_url` in `cursor.py`
2. Update endpoint paths (`/v1/chat`, `/v1/edit`, etc.)
3. Update authentication method
4. Test with real API
