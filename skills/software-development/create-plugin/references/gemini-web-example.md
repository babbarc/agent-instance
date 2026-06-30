# Gemini Web Image Generator

Reference implementation of a CDP-based provider backend plugin. Located at `/opt/data/plugins/image_gen/gemini-web/`.

## What It Does

Wraps the Gemini web interface via Chrome DevTools Protocol (CDP) as an image_gen provider backend.

## Key Pattern

Provider backends don't deal with `task_id` kwargs — only tool-registration plugins do. The provider methods are called by the framework with well-defined signatures from their base classes.