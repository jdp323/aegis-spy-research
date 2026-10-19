import unittest,re
from core.storage import ROOT
class CommandDocumentation(unittest.TestCase):
 def test_registry_and_documented_commands_match_exactly(self):
  source=(ROOT/'monitoring/command_registry.cjs').read_text(encoding='utf-8');registry=set(re.findall(r"\['([a-z_]+)','",source))
  docs=(ROOT/'COMMANDS.md').read_text(encoding='utf-8');documented=set(re.findall(r'^\| /([a-z_]+) \|',docs,re.M));examples=set(re.findall(r'^### /([a-z_]+)$',docs,re.M))
  self.assertEqual(registry,documented);self.assertEqual(registry,examples)
  self.assertEqual(len(registry),36)  # All 35 retained commands plus /details.
