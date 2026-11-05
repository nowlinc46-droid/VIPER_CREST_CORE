import unittest
from unittest.mock import MagicMock, patch

import viper


class LauncherTests(unittest.TestCase):
    def test_each_command_forwards_arguments_and_status(self):
        for command, module in viper.COMMANDS.items():
            with self.subTest(command=command):
                component = MagicMock()
                component.main.return_value = 7
                with patch.object(viper.importlib, "import_module", return_value=component) as load:
                    self.assertEqual(viper.main([command, "--help"]), 7)
                load.assert_called_once_with(module)
                component.main.assert_called_once_with(["--help"])

    def test_aliases_forward_arguments_and_status(self):
        for alias, target in viper.ALIASES.items():
            with self.subTest(alias=alias):
                component = MagicMock()
                component.main.return_value = 5
                with patch.object(viper.importlib, "import_module", return_value=component) as load:
                    self.assertEqual(viper.main([alias, "--help"]), 5)
                load.assert_called_once_with(viper.COMMANDS[target])
                component.main.assert_called_once_with(["--help"])

    def test_missing_or_unknown_command_fails_without_loading_components(self):
        with patch.object(viper.importlib, "import_module") as load:
            for args in ([], ["unknown"]):
                with self.subTest(args=args), self.assertRaises(SystemExit) as raised:
                    viper.main(args)
                self.assertEqual(raised.exception.code, 2)
            load.assert_not_called()
