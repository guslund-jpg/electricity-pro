# Legacy YAML layout placeholders

These directories describe an early YAML-package layout. They currently contain
README files only, not the running Electricity Pro implementation.

The maintained integration is in `custom_components/electricity_pro/`, and user
dashboard examples are in [examples/dashboards](../examples/dashboards/README.md).
Do not copy these placeholders as an integration installation.

The directories are retained because:

- the Home Assistant configuration workflow searches `packages/` for YAML and
  copies any matches into the minimal `config/` validation fixture;
- repository policy and unique-ID checks still scan this layout; and
- existing links and early design material refer to these boundaries.

With no package YAML present, the configuration workflow validates the minimal
fixture, not the Python integration's runtime. Python behaviour is tested
separately; see [development](../docs/development.md).

The old subdirectory descriptions are historical intentions, not restrictions
on today's Python source adapters. Removing or repurposing this layout requires
a separate update of the workflow, validation scripts and references.
