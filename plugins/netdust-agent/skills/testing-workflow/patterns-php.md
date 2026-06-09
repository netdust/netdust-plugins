# PHP Test Patterns

Unit test patterns (PHPUnit / Codeception unit) and acceptance test patterns (Codeception WebDriver).

---

## Unit Test Patterns

### Service Class

```php
class ShippingCalculatorTest extends \Codeception\Test\Unit
{
    private ShippingCalculator $calculator;

    protected function _before(): void
    {
        $this->calculator = new ShippingCalculator();
    }

    public function testCalculatesFreeShippingAboveThreshold(): void
    {
        $cost = $this->calculator->calculate(orderTotal: 150.00, country: 'BE');
        $this->assertEquals(0.00, $cost);
    }

    public function testCalculatesStandardShippingBelowThreshold(): void
    {
        $cost = $this->calculator->calculate(orderTotal: 30.00, country: 'BE');
        $this->assertEquals(5.95, $cost);
    }

    public function testThrowsForUnsupportedCountry(): void
    {
        $this->expectException(UnsupportedCountryException::class);
        $this->calculator->calculate(orderTotal: 50.00, country: 'XX');
    }

    public function testHandlesZeroOrderTotal(): void
    {
        $cost = $this->calculator->calculate(orderTotal: 0.00, country: 'BE');
        $this->assertEquals(5.95, $cost);
    }
}
```

### Data Transformer

```php
class ZoneFormatterTest extends \Codeception\Test\Unit
{
    public function testFormatsZoneForDisplay(): void
    {
        $zone = new Zone(pair: 'BTCUSDT', type: 'demand', score: 8.5);
        $formatted = ZoneFormatter::toDisplay($zone);

        $this->assertArrayHasKey('label', $formatted);
        $this->assertArrayHasKey('strength', $formatted);
        $this->assertEquals('Strong', $formatted['strength']);
    }

    public function testReturnsEmptyArrayForNullInput(): void
    {
        $formatted = ZoneFormatter::toDisplay(null);
        $this->assertEmpty($formatted);
    }

    public function testFormatsMultipleZones(): void
    {
        $zones = [
            new Zone(pair: 'BTCUSDT', type: 'demand', score: 9.0),
            new Zone(pair: 'ETHUSDT', type: 'supply', score: 6.5),
        ];
        $formatted = ZoneFormatter::toDisplayList($zones);

        $this->assertCount(2, $formatted);
        $this->assertEquals('BTCUSDT', $formatted[0]['pair']);
    }
}
```

### Mocking Dependencies

```php
class OrderServiceTest extends \Codeception\Test\Unit
{
    public function testCreatesOrderAndNotifiesCustomer(): void
    {
        // Arrange
        $mailer = $this->createMock(MailerInterface::class);
        $mailer->expects($this->once())
            ->method('send')
            ->with($this->callback(fn($email) =>
                str_contains($email->subject(), 'Order confirmed')
            ));

        $repo = $this->createMock(OrderRepository::class);
        $repo->expects($this->once())
            ->method('save')
            ->willReturn(new Order(id: 42));

        $service = new OrderService($repo, $mailer);

        // Act
        $order = $service->create(items: [['sku' => 'A1', 'qty' => 2]], customer: 'test@example.com');

        // Assert
        $this->assertEquals(42, $order->id);
    }
}
```

### WordPress Hook/Filter

```php
class SeoMetaFilterTest extends \lucatume\WPBrowser\TestCase\WPTestCase
{
    public function testFilterModifiesDocumentTitle(): void
    {
        $plugin = new SeoMetaPlugin();
        $plugin->register();

        // Simulate WordPress calling the filter
        $title = apply_filters('document_title_parts', ['title' => 'Original']);

        $this->assertArrayHasKey('title', $title);
        $this->assertNotEquals('Original', $title['title']);
    }

    public function testFilterSkipsAdminPages(): void
    {
        set_current_screen('dashboard');
        $plugin = new SeoMetaPlugin();
        $plugin->register();

        $title = apply_filters('document_title_parts', ['title' => 'Original']);
        $this->assertEquals('Original', $title['title']);
    }
}
```

### Validation Logic

```php
class ContactFormValidatorTest extends \Codeception\Test\Unit
{
    private ContactFormValidator $validator;

    protected function _before(): void
    {
        $this->validator = new ContactFormValidator();
    }

    public function testAcceptsValidSubmission(): void
    {
        $result = $this->validator->validate([
            'name' => 'Test User',
            'email' => 'test@example.com',
            'message' => 'Hello there',
        ]);
        $this->assertTrue($result->isValid());
    }

    public function testRejectsEmptyName(): void
    {
        $result = $this->validator->validate([
            'name' => '',
            'email' => 'test@example.com',
            'message' => 'Hello',
        ]);
        $this->assertFalse($result->isValid());
        $this->assertArrayHasKey('name', $result->errors());
    }

    public function testRejectsInvalidEmail(): void
    {
        $result = $this->validator->validate([
            'name' => 'Test',
            'email' => 'not-an-email',
            'message' => 'Hello',
        ]);
        $this->assertFalse($result->isValid());
        $this->assertArrayHasKey('email', $result->errors());
    }

    public function testSanitizesHtmlInMessage(): void
    {
        $result = $this->validator->validate([
            'name' => 'Test',
            'email' => 'test@example.com',
            'message' => '<script>alert("xss")</script>Hello',
        ]);
        $this->assertTrue($result->isValid());
        $this->assertStringNotContainsString('<script>', $result->sanitized()['message']);
    }
}
```

### Configuration / Settings

```php
class PluginSettingsTest extends \Codeception\Test\Unit
{
    public function testReturnsDefaultsWhenNoSettingsSaved(): void
    {
        $settings = new PluginSettings();
        $this->assertEquals('light', $settings->get('theme'));
        $this->assertEquals(10, $settings->get('per_page'));
    }

    public function testOverridesDefaultsWithSavedValues(): void
    {
        $settings = new PluginSettings(['theme' => 'dark']);
        $this->assertEquals('dark', $settings->get('theme'));
        $this->assertEquals(10, $settings->get('per_page')); // default preserved
    }

    public function testIgnoresUnknownKeys(): void
    {
        $settings = new PluginSettings(['unknown_key' => 'value']);
        $this->assertNull($settings->get('unknown_key'));
    }
}
```

---

## Acceptance Test Patterns

### Form with AJAX Submission

```php
$I->amOnPage('/form');
$I->seeElement('form#my-form');
$I->fillField('#field', 'value');
$I->click('#submit');
$I->waitForElementVisible('.success-message', 10);
// Verify persistence — AJAX can show success without saving
$I->seeInDatabase('table_name', ['column' => 'value']);
```

### Form with Page Reload

```php
$I->amOnPage('/contact');
$I->fillField('#name', 'Test User');
$I->fillField('#email', 'test@example.com');
$I->click('Send');
$I->see('Thank you');
$I->seeInDatabase('submissions', ['email' => 'test@example.com']);
```

### Form Validation (Rejection)

```php
$I->amOnPage('/form');
$I->click('#submit'); // Submit empty
$I->dontSee('Thank you');
$I->waitForElementVisible('.field-error', 5);
$I->dontSeeInDatabase('submissions', ['email' => '']);
```

### Admin Dashboard Screen

```php
$I->login('admin@example.com', 'password');
$I->amOnPage('/admin/settings');
$I->see('Settings');
$I->fillField('#option', 'new-value');
$I->click('Save');
$I->waitForText('Saved', 10);
$I->seeInDatabase('settings', ['key' => 'option', 'value' => 'new-value']);
```

### REST/API Called from Frontend

```php
$I->amOnPage('/page-calling-api');
$I->click('#load-data');
$I->waitForElementVisible('.data-container', 10);
$I->see('Expected data');
$I->dontSee('Error');
$I->dontSee('undefined');
```

### Page Loads Without Errors

```php
$I->amOnPage('/the-page');
$I->seeResponseCodeIs(200);
$I->seeElement('body');
$I->dontSee('Fatal error');
$I->dontSee('Warning:');
$I->dontSee('Parse error');
```

### JavaScript Error Check

```php
public function pageHasNoJsErrors(AcceptanceTester $I): void
{
    $I->amOnPage('/the-page');
    $I->waitForElement('body', 5);
    $logs = $I->executeInSelenium(
        fn($wd) => $wd->manage()->getLog('browser')
    );
    $errors = array_filter($logs, fn($l) => $l['level'] === 'SEVERE');
    if (count($errors) > 0) {
        $I->fail('JS errors: ' . implode("\n", array_column($errors, 'message')));
    }
}
```

### Authentication & Role-Based Access

```php
// Regular user should NOT see admin page
$I->login('user@example.com', 'password');
$I->amOnPage('/admin/settings');
$I->dontSee('Settings');
$I->see('Access denied');
```

### Database Fixtures

```php
$I->haveInDatabase('users', [
    'email' => 'test@example.com',
    'name' => 'Test User',
    'status' => 'active',
]);
$I->amOnPage('/users');
$I->see('Test User');
```

---

## Wait Patterns

**Never use fixed waits.** Use condition-based waits.

```php
// ❌ BAD
$I->wait(5);

// ✅ GOOD
$I->waitForElement('.element', 10);
$I->waitForText('Success', 10);
$I->waitForElementVisible('.modal', 10);
$I->waitForElementNotVisible('.loading', 10);
```
