describe('Recommendations', () => {
  beforeEach(() => {
    // Login before each test
    cy.login();
  });

  it('should load and display recommendations', () => {
    cy.visit('/dashboard');
    cy.get('[data-testid="recommendation-list"]').should('exist');
    cy.get('[data-testid="recommendation-item"]').should('have.length.at.least', 1);
  });

  it('should filter recommendations by category', () => {
    cy.visit('/dashboard');
    cy.get('[data-testid="category-filter"]').select('test');
    cy.get('[data-testid="recommendation-item"]')
      .should('exist')
      .each($el => {
        cy.wrap($el).find('[data-testid="category-badge"]')
          .should('contain.text', 'test');
      });
  });

  it('should paginate through recommendations', () => {
    cy.visit('/dashboard');
    cy.get('[data-testid="next-page"]').click();
    cy.get('[data-testid="page-number"]').should('contain.text', '2');
    cy.get('[data-testid="recommendation-item"]').should('exist');
  });
}); 