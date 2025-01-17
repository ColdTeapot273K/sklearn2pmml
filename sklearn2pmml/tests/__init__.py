from pandas import Categorical, CategoricalDtype, DataFrame, Series
from sklearn.dummy import DummyRegressor
from sklearn.feature_selection import f_regression, SelectFromModel, SelectKBest
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeRegressor
from sklearn2pmml import _classpath, _filter, _filter_steps, _is_categorical, _java_version, _parse_java_version, _strip_module, _supported_classes, make_pmml_pipeline, make_tpot_pmml_config, EstimatorProxy, SelectorProxy
from sklearn2pmml.pipeline import PMMLPipeline
from unittest import TestCase

import numpy

class DTypeTest(TestCase):

	def test_is_categorical(self):
		x = Series(["True", "False", "True"], name = "x", dtype = str)
		self.assertEqual(["True", "False", "True"], x.values.tolist())
		self.assertTrue(_is_categorical(x.dtype))
		x = Series([True, False, True], name = "x", dtype = bool)
		self.assertEqual([True, False, True], x.values.tolist())
		self.assertTrue(_is_categorical(x.dtype))
		x = x.astype(float)
		self.assertEqual([1.0, 0.0, 1.0], x.values.tolist())
		self.assertFalse(_is_categorical(x.dtype))
		x = x.astype("category")
		self.assertEqual([1.0, 0.0, 1.0], x.values.tolist())
		self.assertTrue(_is_categorical(x.dtype))
		x = x.astype(int)
		self.assertEqual([1, 0, 1], x.values.tolist())
		self.assertFalse(_is_categorical(x.dtype))
		x = x.astype(CategoricalDtype())
		self.assertEquals([1, 0, 1], x.values.tolist())
		self.assertTrue(_is_categorical(x.dtype))

class EstimatorProxyTest(TestCase):

	def test_init(self):
		regressor = DummyRegressor()
		regressor.fit(numpy.array([[0], [0]]), numpy.array([0.0, 2.0]))
		self.assertEqual(1.0, regressor.constant_)
		regressor_proxy = EstimatorProxy(regressor, attr_names = ["constant_"])
		self.assertEqual(1.0, regressor_proxy.constant_)

	def test_fit(self):
		regressor = DummyRegressor()
		regressor_proxy = EstimatorProxy(regressor, attr_names = ["constant_"])
		self.assertFalse(hasattr(regressor_proxy, "constant_"))
		regressor_proxy.fit(numpy.array([[0], [0]]), numpy.array([0.0, 2.0]))
		self.assertEqual(1.0, regressor.constant_)
		self.assertEqual(1.0, regressor_proxy.constant_)

class SelectorProxyTest(TestCase):

	def test_init(self):
		selector = SelectKBest(score_func = f_regression, k = 1)
		selector.fit(numpy.array([[0, 0], [1.0, 2.0]]), numpy.array([0.5, 1.0]))
		self.assertEqual([0, 1], selector._get_support_mask().tolist())
		selector_proxy = SelectorProxy(selector)
		self.assertEqual([0, 1], selector_proxy.support_mask_.tolist())

	def test_fit(self):
		selector = SelectKBest(score_func = f_regression, k = 1)
		selector_proxy = SelectorProxy(selector)
		self.assertFalse(hasattr(selector_proxy, "support_mask_"))
		selector_proxy.fit(numpy.array([[0, 0], [1.0, 2.0]]), numpy.array([0.5, 1.0]))
		self.assertEqual([0, 1], selector._get_support_mask().tolist())
		self.assertEqual([0, 1], selector_proxy.support_mask_.tolist())

	def test_filter(self):
		selector = SelectFromModel(DecisionTreeRegressor(), prefit = False)
		self.assertIsInstance(selector, SelectFromModel)
		self.assertIsInstance(selector.estimator, DecisionTreeRegressor)
		self.assertFalse(hasattr(selector, "estimator_"))
		selector_proxy = _filter_steps([("selector", selector)])[0][1]
		self.assertIsInstance(selector_proxy, SelectorProxy)
		selector_proxy.fit(numpy.array([[0, 1], [0, 2], [0, 3]]), numpy.array([0.5, 1.0, 1.5]))
		self.assertEqual([0, 1], selector_proxy.support_mask_.tolist())

	def test_filter_prefit(self):
		regressor = DecisionTreeRegressor()
		regressor.fit(numpy.array([[0, 1], [0, 2], [0, 3]]), numpy.array([0.5, 1.0, 1.5]))
		selector = SelectFromModel(regressor, prefit = True)
		self.assertTrue(hasattr(selector, "estimator"))
		self.assertFalse(hasattr(selector, "estimator_"))
		selector_proxy = _filter_steps([("selector", selector, {})])[0][1]
		self.assertIsInstance(selector_proxy, SelectorProxy)
		self.assertEqual([0, 1], selector_proxy.support_mask_.tolist())

class JavaTest(TestCase):

	def test_java_version(self):
		version = _java_version()
		self.assertIsInstance(version, tuple)
		self.assertTrue(2, len(version))

	def test_parse_java_version(self):
		"""Example Java LTS version strings.

		Obtained via:
		$JAVA_HOME/bin/java -version > /dev/null
		"""
		java_version_string = 'java version "1.8.0_202"\n' \
			'Java(TM) SE Runtime Environment (build 1.8.0_202-b08)\n' \
			'Java HotSpot(TM) 64-Bit Server VM (build 25.202-b08, mixed mode)'
		version = _parse_java_version(java_version_string)
		self.assertEqual(("java", "1.8.0_202"), version)

		java_version_string = 'java version "11.0.2" 2019-01-15 LTS\n' \
			'Java(TM) SE Runtime Environment 18.9 (build 11.0.2+9-LTS)\n' \
			'Java HotSpot(TM) 64-Bit Server VM 18.9 (build 11.0.2+9-LTS, mixed mode)'
		version = _parse_java_version(java_version_string)
		self.assertEqual(("java", "11.0.2"), version)

		java_version_string = 'java version "17.0.1" 2021-10-19 LTS\n' \
			'Java(TM) SE Runtime Environment (build 17.0.1+12-LTS-39)\n' \
			'Java HotSpot(TM) 64-Bit Server VM (build 17.0.1+12-LTS-39, mixed mode, sharing)'
		version = _parse_java_version(java_version_string)
		self.assertEqual(("java", "17.0.1"), version)

class ClasspathTest(TestCase):

	def test_classpath(self):
		classpath = _classpath([])
		self.assertEqual(31, len(classpath))
		classpath = _classpath(["A.jar", "B.jar"])
		self.assertEqual(31 + 2, len(classpath))

	def test_supported_classes(self):
		classes = _supported_classes([])
		self.assertTrue(len(classes) > 100)

	def test_strip_module(self):
		self.assertEqual("sklearn.decomposition.PCA", _strip_module("sklearn.decomposition.pca.PCA"))
		self.assertEqual("sklearn.feature_selection.SelectPercentile", _strip_module("sklearn.feature_selection.univariate_selection.SelectPercentile"))
		self.assertEqual("sklearn.preprocessing.StandardScaler", _strip_module("sklearn.preprocessing.data.StandardScaler"))
		self.assertEqual("sklearn.tree.DecisionTreeClassifier", _strip_module("sklearn.tree.tree.DecisionTreeClassifier"))

class FunctionTest(TestCase):

	def test_make_pmml_pipeline(self):
		with self.assertRaises(TypeError):
			make_pmml_pipeline(None)
		estimator = DummyRegressor()
		pmml_pipeline = make_pmml_pipeline(estimator)
		self.assertTrue(isinstance(pmml_pipeline, PMMLPipeline))
		pipeline = Pipeline([
			("estimator", estimator)
		])
		pmml_pipeline = make_pmml_pipeline(pipeline)
		self.assertTrue(isinstance(pmml_pipeline, PMMLPipeline))

	def test_make_tpot_pmml_config(self):
		config = {
			"sklearn.kernel_approximation.RBFSampler" : {"gamma" : numpy.arange(0.0, 1.01, 0.05)},
			"sklearn.preprocessing.StandardScaler" : {}
		}
		tpot_pmml_config = make_tpot_pmml_config(config)
		self.assertEqual({"sklearn.preprocessing.StandardScaler" : {}}, tpot_pmml_config)
